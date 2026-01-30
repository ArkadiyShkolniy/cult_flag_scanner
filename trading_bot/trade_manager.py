import json
import os
import uuid
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from t_tech.invest import Client, OrderDirection, OrderType, InstrumentIdType
from t_tech.invest.utils import quotation_to_decimal, decimal_to_quotation

class TradeManager:
    """
    Класс управления сделками: расчет объема, отправка ордеров, учет позиций, сбор данных для ML.
    """
    def __init__(self, token, account_id=None, risk_per_trade=0.01, dry_run=True, debug_mode=True, use_ai_filter=True, data_dir="trading_bot", logger=None):
        """
        Args:
            token: API токен
            account_id: ID торгового счета
            risk_per_trade: Риск на сделку (0.01 = 1%)
            dry_run: True = эмуляция торгов
            debug_mode: True = всегда торговать 1 лотом (для отладки)
            use_ai_filter: True = использовать ML модель для фильтрации сделок
            data_dir: Папка для хранения данных (истории, конфигов)
            logger: Logger объект для логирования (если None, используется print)
        """
        self.token = token
        self.risk_per_trade = risk_per_trade
        self.dry_run = dry_run
        self.debug_mode = debug_mode
        self.account_id = account_id
        self.use_ai_filter = use_ai_filter
        self.logger = logger
        
        # Комиссия брокера (0.04% = 0.0004)
        self.commission_rate = 0.0004
        
        # --- Файловая структура ---
        self.base_dir = Path(data_dir)
        # Создаем директорию, если её нет
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_path = Path("neural_network/models/trading_model_rf.pkl")
        
        # Активные сделки (JSON)
        self.trades_file = self.base_dir / "trades_active.json"
        
        # Конфигурация торговли (JSON)
        self.config_file = self.base_dir / "trading_config.json"
        
        # История закрытых сделок (JSON)
        self.history_file = self.base_dir / "trades_history.json"
        
        # Данные для обучения ML
        self.training_dir = self.base_dir / "training_data"
        self.snapshots_dir = self.training_dir / "snapshots"
        self.dataset_file = self.training_dir / "dataset_v1.csv"
        
        # Создаем директории
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Инициализация CSV датасета
        if not self.dataset_file.exists():
            with open(self.dataset_file, 'w') as f:
                # Заголовок датасета
                f.write("trade_id,ticker,direction,entry_time,exit_time,entry_price,exit_price,pnl_net,result_type,mae,mfe,hold_time_minutes,stop_loss,take_profit,pattern_score,snapshot_file,ai_probability\n")
        
        # Загрузка состояния
        self.active_trades = self._load_json(self.trades_file, is_dict=True)
        self.closed_trades = self._load_json(self.history_file, is_dict=False)
        
        # Загрузка AI модели
        self.ai_model = None
        if self.use_ai_filter:
            if self.model_path.exists():
                try:
                    self.ai_model = joblib.load(self.model_path)
                    self._log(f"✅ AI Модель загружена: {self.model_path}")
                except Exception as e:
                    self._log(f"⚠️ Ошибка загрузки AI модели: {e}", 'warning')
            else:
                self._log(f"⚠️ AI Модель не найдена по пути {self.model_path}", 'warning')

        if not self.dry_run and not self.account_id:
            self._fetch_account_id()
    
    def _log(self, message, level='info'):
        """Вспомогательный метод для логирования"""
        if self.logger:
            if level == 'info':
                self.logger.info(message)
            elif level == 'warning':
                self.logger.warning(message)
            elif level == 'error':
                self.logger.error(message)
            else:
                self.logger.info(message)
        else:
            print(message)

    def _load_json(self, path, is_dict=True):
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                return {} if is_dict else []
        return {} if is_dict else []

    def _save_active_trades(self):
        with open(self.trades_file, 'w') as f:
            json.dump(self.active_trades, f, indent=4, default=str)

    def _save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.closed_trades, f, indent=4, default=str)

    def _fetch_account_id(self):
        """Получает ID первого брокерского счета"""
        try:
            with Client(self.token) as client:
                accounts = client.users.get_accounts()
                self.account_id = accounts.accounts[0].id
                self._log(f"✅ TradeManager: Используем счет {self.account_id}")
        except Exception as e:
            self._log(f"❌ Ошибка получения счета: {e}", 'error')

    def _get_portfolio_value(self):
        """Получает текущую стоимость портфеля"""
        if self.dry_run:
            return 100000.0  # Виртуальные 100к
        try:
            with Client(self.token) as client:
                portfolio = client.operations.get_portfolio(account_id=self.account_id)
                amount = quotation_to_decimal(portfolio.total_amount_portfolio)
                return float(amount)
        except Exception as e:
            self._log(f"⚠️ Не удалось получить баланс: {e}", 'warning')
            return 100000.0

    def _get_lot_size(self, uid):
        """Получает размер лота"""
        if self.dry_run:
            return 1
        try:
            with Client(self.token) as client:
                instrument = client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID, 
                    id=uid
                ).instrument
                return instrument.lot
        except:
            return 1

    def calculate_quantity(self, entry_price, stop_loss, instrument_uid):
        """
        Рассчитывает количество лотов.
        - Если в конфиге задан fixed_lot_size > 0 — используется он (и в DEBUG, и в PROD).
        - Иначе в DEBUG — 1 лот по умолчанию, в PROD — расчёт по риску (risk_amount / loss_per_lot).
        """
        config = self._load_json(self.config_file)
        fixed_lot = config.get('fixed_lot_size')
        if fixed_lot is not None:
            try:
                n = int(fixed_lot)
                if n > 0:
                    return n, self._get_lot_size(instrument_uid)
            except (TypeError, ValueError):
                pass

        # В режиме отладки без fixed_lot_size — по умолчанию 1 лот
        if self.debug_mode:
            return 1, self._get_lot_size(instrument_uid)

        # PROD: расчёт по риску (даёт много лотов при большом портфеле/малом стопе)
        portfolio_value = self._get_portfolio_value()
        risk_amount = portfolio_value * self.risk_per_trade
        
        loss_per_share = abs(entry_price - stop_loss)
        if loss_per_share == 0: return 0, 1
        
        lot_size = self._get_lot_size(instrument_uid)
        loss_per_lot = loss_per_share * lot_size
        
        if loss_per_lot == 0: return 0, lot_size
        
        quantity = int(risk_amount / loss_per_lot)
        if quantity < 1: quantity = 0
        
        return quantity, lot_size
        
    def _predict_success(self, pattern_info, entry_price, stop_loss, take_profit):
        """
        Использует AI модель для оценки вероятности успеха сделки.
        Возвращает: (is_good: bool, probability: float)
        """
        if not self.ai_model or not pattern_info:
            return True, 0.5 # Если модели нет, пропускаем всех (neutral)
            
        try:
            # 1. Извлечение признаков (Feature Extraction)
            # Должно полностью совпадать с generate_trading_dataset.py / train_trading_model.py
            
            t0 = pattern_info['t0']['price']
            t1 = pattern_info['t1']['price']
            t2 = pattern_info['t2']['price']
            t3 = pattern_info['t3']['price']
            
            # Индексы (для наклона)
            t1_idx = pattern_info['t1']['idx']
            t3_idx = pattern_info['t3']['idx']
            
            # correction_ratio
            pole_height = abs(t1 - t0)
            correction_depth = abs(t2 - t1)
            correction_ratio = correction_depth / pole_height if pole_height != 0 else 0
            
            # slope_channel
            slope_channel = (t3 - t1) / (t3_idx - t1_idx) if (t3_idx - t1_idx) != 0 else 0
            
            # risk_reward_ratio
            rr_ratio = abs(take_profit - entry_price) / abs(entry_price - stop_loss) if abs(entry_price - stop_loss) != 0 else 0
            
            # Формируем DataFrame (модель ожидает имена колонок)
            features = pd.DataFrame([{
                'correction_ratio': correction_ratio,
                'slope_channel': slope_channel,
                'risk_reward_ratio': rr_ratio
            }])
            
            # 2. Прогноз
            # predict_proba возвращает [[prob_0, prob_1]]
            probability = self.ai_model.predict_proba(features)[0][1]
            
            # Порог принятия решения (например, > 50%)
            # Можно сделать настраиваемым параметром
            is_good = probability > 0.5
            
            return is_good, probability
            
        except Exception as e:
            self._log(f"⚠️ Ошибка AI прогноза: {e}", 'warning')
            return True, 0.5

    def open_position(self, ticker, uid, direction, price, stop_loss, take_profit, strategy_desc, df_context=None, pattern_info=None, entry_mode=None):
        """
        Открывает позицию и сохраняет данные для ML.
        """
        if ticker in self.active_trades:
            self._log(f"⚠️ Позиция {ticker} уже открыта, пропускаем", 'warning')
            return
            
        self._log(f"\n🔔 СИГНАЛ НА ВХОД: {ticker} ({direction})")
        self._log(f"   Цена: {price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
        
        # --- AI ФИЛЬТР ---
        ai_prob = 0.0
        if self.use_ai_filter:
            if self.ai_model:
                is_good, ai_prob = self._predict_success(pattern_info, price, stop_loss, take_profit)
                if not is_good:
                    self._log(f"🤖 AI FILTER: Сделка отклонена. Вероятность успеха {ai_prob:.1%} < 50%", 'warning')
                    return
                else:
                    self._log(f"🤖 AI FILTER: Одобрено! Вероятность успеха {ai_prob:.1%}")
            else:
                # Если AI фильтр включен, но модель не загружена - пропускаем фильтр и продолжаем
                self._log(f"⚠️ AI FILTER включен, но модель не загружена. Пропускаем фильтр и продолжаем", 'warning')
        
        quantity_lots, lot_size = self.calculate_quantity(price, stop_loss, uid)
        self._log(f"   📊 Расчет объема: {quantity_lots} лотов (lot_size={lot_size})")
        
        if quantity_lots == 0:
            self._log(f"❌ Отмена: 0 лотов (недостаточно капитала или риск велик)", 'warning')
            portfolio_value = self._get_portfolio_value()
            risk_amount = portfolio_value * self.risk_per_trade
            loss_per_share = abs(price - stop_loss)
            self._log(f"   Детали: portfolio={portfolio_value:.2f}, risk_per_trade={self.risk_per_trade}, risk_amount={risk_amount:.2f}, loss_per_share={loss_per_share:.2f}")
            return

        # Рассчитываем комиссию
        position_value = price * quantity_lots * lot_size
        commission = position_value * self.commission_rate

        self._log(f"   📊 Параметры сделки:")
        self._log(f"      Цена: {price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
        self._log(f"      Объем: {quantity_lots} лотов (x{lot_size}) = {position_value:.2f} руб.")
        self._log(f"      Комиссия входа: {commission:.2f} руб.")
        
        # Московское время (UTC+3)
        moscow_tz = timezone(timedelta(hours=3))
        moscow_time = datetime.now(timezone.utc).astimezone(moscow_tz)
        # Tinkoff API: order_id должен быть пустым или UUID
        order_id = str(uuid.uuid4())
        trade_id = moscow_time.strftime("%Y%m%d_%H%M%S") + "_" + ticker
        
        # --- ML: Сохранение контекста (снэпшот) ---
        snapshot_filename = ""
        if df_context is not None and not df_context.empty:
            snapshot_filename = f"{trade_id}.csv"
            try:
                # Сохраняем последние 200 свечей
                df_save = df_context.tail(200).copy()
                df_save.to_csv(self.snapshots_dir / snapshot_filename, index=False)
                
                # Сохраняем паттерн
                if pattern_info:
                    with open(self.snapshots_dir / f"{trade_id}_pattern.json", 'w') as f:
                        json.dump(pattern_info, f, default=str, indent=2)
            except Exception as e:
                self._log(f"⚠️ Ошибка сохранения снэпшота: {e}", 'warning')

        trade = {
            'id': trade_id,
            'ticker': ticker,
            'uid': uid,
            'direction': direction,
            'entry_time': datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=3))).isoformat(),
            'entry_price': price,
            'quantity_lots': quantity_lots,
            'lot_size': lot_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'commission_entry': commission,
            'status': 'OPEN',
            'strategy_desc': strategy_desc,
            'entry_mode': entry_mode,  # Сохраняем режим входа
            # Метрики ML
            'mae': 0.0,
            'mfe': 0.0,
            'snapshot_file': snapshot_filename,
            'ai_probability': ai_prob
        }

        if not self.dry_run:
            # Реальная отправка заявки через Tinkoff Invest API
            try:
                self._log(f"   📤 ОТПРАВКА ЗАЯВКИ: {direction} {quantity_lots} лотов {ticker} по цене {price:.2f}")
                with Client(self.token) as client:
                    order_direction = OrderDirection.ORDER_DIRECTION_BUY if direction == 'LONG' else OrderDirection.ORDER_DIRECTION_SELL
                    order_type = OrderType.ORDER_TYPE_MARKET
                    quantity = quantity_lots
                    instrument_info = client.instruments.get_instrument_by(
                        id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
                        id=uid
                    ).instrument
                    figi = instrument_info.figi
                    self._log(f"      Инструмент: {ticker}, FIGI: {figi}, UID: {uid}")
                    order_response = client.orders.post_order(
                        account_id=self.account_id,
                        figi=figi,
                        quantity=quantity,
                        price=None,
                        direction=order_direction,
                        order_type=order_type,
                        order_id=order_id
                    )
                    if order_response:
                        self._log(f"      ✅ Заявка отправлена успешно! Order ID: {order_id}")
                        trade['order_id'] = order_id
                        trade['order_status'] = 'SUBMITTED'
                    else:
                        self._log(f"      ⚠️ Заявка отправлена, но ответ пустой", 'warning')
                        trade['order_id'] = order_id
                        trade['order_status'] = 'UNKNOWN'
            except Exception as e:
                self._log(f"      ❌ ОШИБКА отправки заявки: {e}", 'error')
                import traceback
                self._log(f"      {traceback.format_exc()}", 'error')
                trade['order_id'] = None
                trade['order_status'] = 'ERROR'
                trade['order_error'] = str(e)
        else:
            self._log(f"   🧪 DRY RUN: Эмуляция открытия позиции (реальная заявка не отправляется)")

        # В active_trades добавляем только при успешной заявке или в dry_run (иначе на счете нет позиции, а в боте — есть)
        if self.dry_run or trade.get('order_status') in ('SUBMITTED', 'UNKNOWN'):
            self.active_trades[ticker] = trade
            self._save_active_trades()
            action = "🟢 КУПЛЕНО" if direction == 'LONG' else "🔴 ПРОДАНО"
            mode_text = "DRY RUN" if self.dry_run else "РЕАЛЬНАЯ СДЕЛКА"
            self._log(f"✅ {action} {quantity_lots} лотов {ticker}. {strategy_desc} [{mode_text}]")
        else:
            self._log(f"   ⚠️ Позиция НЕ добавлена в active_trades: заявка не исполнена (order_status={trade.get('order_status', 'ERROR')}). На реальном счёте позиции нет.", 'warning')

    def update_positions(self, current_prices):
        """
        Проверяет выходы и обновляет MFE/MAE.
        """
        to_remove = []
        
        for ticker, trade in self.active_trades.items():
            if ticker not in current_prices:
                continue
                
            current_data = current_prices[ticker]
            current_price = current_data['price']
            
            direction = trade['direction']
            entry_price = trade['entry_price']
            stop_loss = trade['stop_loss']
            take_profit = trade['take_profit']
            
            # --- Обновление MFE/MAE ---
            price_change = current_price - entry_price
            
            # Для шорта прибыль - это падение цены (отрицательный change)
            # Превратим в "пункты прибыли":
            if direction == 'SHORT':
                points_profit = -price_change
            else:
                points_profit = price_change
                
            # MFE (максимальная прибыль в моменте)
            if points_profit > trade.get('mfe', 0):
                trade['mfe'] = points_profit
                
            # MAE (максимальный убыток/просадка в моменте)
            # MAE всегда <= 0 (или tracking drawdown)
            if points_profit < trade.get('mae', 0):
                trade['mae'] = points_profit
            
            close_reason = None
            
            if direction == 'LONG':
                if current_price >= take_profit:
                    close_reason = f"TAKE PROFIT"
                elif current_price <= stop_loss:
                    close_reason = f"STOP LOSS"
            elif direction == 'SHORT':
                if current_price <= take_profit:
                    close_reason = f"TAKE PROFIT"
                elif current_price >= stop_loss:
                    close_reason = f"STOP LOSS"
            
            if close_reason:
                self._close_position(ticker, trade, current_price, close_reason, current_data['time'])
                to_remove.append(ticker)
        
        # Если были обновления MFE/MAE, сохраняем состояние
        if not to_remove and self.active_trades:
            self._save_active_trades()
                
        for t in to_remove:
            del self.active_trades[t]
        
        if to_remove:
            self._save_active_trades()
            self.print_statistics()

    def _close_position(self, ticker, trade, exit_price, reason, exit_time):
        quantity = trade.get('quantity_lots')
        lot_size = trade.get('lot_size')
        if quantity is None or (isinstance(quantity, (int, float)) and quantity <= 0):
            self._log(f"   ⚠️ quantity_lots отсутствует или ≤ 0 ({quantity}), используем 1", 'warning')
            quantity = 1
        if lot_size is None or (isinstance(lot_size, (int, float)) and lot_size <= 0):
            self._log(f"   ⚠️ lot_size отсутствует или ≤ 0 ({lot_size}), используем 1", 'warning')
            lot_size = 1
        quantity = int(quantity)
        lot_size = int(lot_size)
        entry_price = trade['entry_price']
        direction = trade['direction']
        
        # Расчет финансов: объём в штуках = лоты × размер лота
        position_value_exit = exit_price * quantity * lot_size
        commission_exit = position_value_exit * self.commission_rate
        total_commission = trade['commission_entry'] + commission_exit
        
        if direction == 'LONG':
            gross_profit = (exit_price - entry_price) * quantity * lot_size
        else: # SHORT
            gross_profit = (entry_price - exit_price) * quantity * lot_size
            
        net_profit = gross_profit - total_commission
        
        self._log(f"\n⚖️ ЗАКРЫТИЕ ПОЗИЦИИ {ticker} ({direction})")
        self._log(f"   Причина: {reason}")
        self._log(f"   Вход: {entry_price:.2f} -> Выход: {exit_price:.2f}")
        self._log(f"   P&L (грязный): {gross_profit:.2f} руб.")
        self._log(f"   Комиссия: {total_commission:.2f} руб.")
        self._log(f"   P&L (чистый): {net_profit:.2f} руб.")
        self._log(f"   MFE: {trade.get('mfe', 0):.2f} | MAE: {trade.get('mae', 0):.2f}")
        
        if not self.dry_run:
            # Реальная заявка на закрытие: LONG закрываем продажей, SHORT — покупкой
            try:
                uid = trade.get('uid')
                if not uid:
                    self._log(f"      ❌ ОШИБКА: в сделке нет uid, закрытие на бирже невозможно", 'error')
                else:
                    close_direction = OrderDirection.ORDER_DIRECTION_SELL if direction == 'LONG' else OrderDirection.ORDER_DIRECTION_BUY
                    self._log(f"   📤 ОТПРАВКА ЗАЯВКИ НА ЗАКРЫТИЕ: {'SELL' if direction == 'LONG' else 'BUY'} {quantity} лотов {ticker} (рынок)")
                    with Client(self.token) as client:
                        instrument_info = client.instruments.get_instrument_by(
                            id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
                            id=uid
                        ).instrument
                        figi = instrument_info.figi
                        close_order_id = str(uuid.uuid4())
                        order_response = client.orders.post_order(
                            account_id=self.account_id,
                            figi=figi,
                            quantity=quantity,
                            price=None,
                            direction=close_direction,
                            order_type=OrderType.ORDER_TYPE_MARKET,
                            order_id=close_order_id
                        )
                        if order_response:
                            self._log(f"      ✅ Заявка на закрытие отправлена. Order ID: {close_order_id}")
                        else:
                            self._log(f"      ⚠️ Заявка на закрытие отправлена, но ответ пустой", 'warning')
            except Exception as e:
                self._log(f"      ❌ ОШИБКА отправки заявки на закрытие: {e}", 'error')
                import traceback
                self._log(traceback.format_exc(), 'error')
        else:
            self._log(f"   🧪 DRY RUN: Эмуляция закрытия позиции (реальная заявка не отправляется)")

        # Финализация записи
        trade['exit_time'] = str(exit_time)
        trade['exit_price'] = exit_price
        trade['status'] = 'CLOSED'
        trade['close_reason'] = reason
        trade['gross_profit'] = gross_profit
        trade['commission_total'] = total_commission
        trade['net_profit'] = net_profit
        
        if isinstance(self.closed_trades, list):
            self.closed_trades.append(trade)
        else:
            self.closed_trades = [trade]
            
        self._save_history()
        
        # --- ML: Запись в датасет ---
        try:
            entry_dt = datetime.fromisoformat(trade['entry_time'])
            if isinstance(exit_time, str):
                exit_dt = datetime.fromisoformat(exit_time)
            else:
                exit_dt = exit_time
                
            hold_time_minutes = (exit_dt - entry_dt).total_seconds() / 60
            result_type = "WIN" if net_profit > 0 else "LOSS"
            
            with open(self.dataset_file, 'a') as f:
                # trade_id,ticker,direction,entry_time,exit_time,entry_price,exit_price,pnl_net,result_type,mae,mfe,hold_time_minutes,stop_loss,take_profit,pattern_score,snapshot_file,ai_probability
                f.write(f"{trade['id']},{ticker},{direction},{trade['entry_time']},{trade['exit_time']},"
                        f"{entry_price},{exit_price},{net_profit:.2f},{result_type},"
                        f"{trade.get('mae', 0):.2f},{trade.get('mfe', 0):.2f},{hold_time_minutes:.1f},"
                        f"{trade['stop_loss']},{trade['take_profit']},0,{trade['snapshot_file']},"
                        f"{trade.get('ai_probability', 0):.4f}\n")
            self._log(f"   💾 Данные для ML сохранены в {self.dataset_file}")
            
        except Exception as e:
            self._log(f"❌ Ошибка сохранения датасета ML: {e}", 'error')

    def close_all_positions(self, current_prices):
        """
        Принудительно закрывает все активные позиции.
        Args:
            current_prices: Словарь {ticker: {'price': float, 'time': str}}
        """
        self._log(f"\n🚨 ПРИНУДИТЕЛЬНОЕ ЗАКРЫТИЕ ВСЕХ ПОЗИЦИЙ ({len(self.active_trades)})")
        
        # Создаем список тикеров для закрытия, чтобы не менять словарь во время итерации
        tickers_to_close = list(self.active_trades.keys())
        
        for ticker in tickers_to_close:
            trade = self.active_trades[ticker]
            
            # Получаем цену закрытия
            if ticker in current_prices:
                exit_price = current_prices[ticker]['price']
                exit_time = current_prices[ticker]['time']
                
                # Защита от нулевой цены (если API вернул 0 или ошибка)
                if exit_price <= 0:
                    self._log(f"⚠️ Некорректная цена закрытия {exit_price} для {ticker}, используем цену входа", 'warning')
                    exit_price = trade.get('entry_price', 0)
            else:
                # Если цены нет, закрываем по цене входа (экстренный случай)
                self._log(f"⚠️ Нет текущей цены для {ticker}, закрываем по цене входа", 'warning')
                exit_price = trade.get('entry_price', 0)
                exit_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=3))).isoformat()
            
            # Если даже entry_price = 0, то ничего не поделаешь, но хотя бы не будет огромного минуса/плюса
            if exit_price <= 0:
                 self._log(f"⚠️ Цена закрытия все еще 0 для {ticker}, P&L будет некорректным", 'warning')
            
            # Закрываем позицию
            self._close_position(ticker, trade, exit_price, "MANUAL CLOSE ALL", exit_time)
        
        # Очищаем список активных сделок
        self.active_trades = {}
        self._save_active_trades()
        self.print_statistics()

    def print_statistics(self):
        """Выводит сводную статистику"""
        if not self.closed_trades or not isinstance(self.closed_trades, list):
            return

        total_trades = len(self.closed_trades)
        total_profit = sum(t['net_profit'] for t in self.closed_trades)
        wins = sum(1 for t in self.closed_trades if t['net_profit'] > 0)
        losses = total_trades - wins
        
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        self._log("\n" + "="*40)
        self._log("📊 СТАТИСТИКА ТОРГОВЛИ")
        self._log(f"   Всего сделок: {total_trades}")
        self._log(f"   Прибыльных: {wins} ({win_rate:.1f}%) | Убыточных: {losses}")
        self._log(f"   Общий P&L: {total_profit:.2f} руб.")
        self._log("="*40 + "\n")