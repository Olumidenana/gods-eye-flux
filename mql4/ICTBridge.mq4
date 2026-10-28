//+------------------------------------------------------------------+
//| ICTBridge.mq4                                                     |
//| File bridge between MetaTrader 4 and the ict_trader Python engine. |
//|                                                                   |
//| Attach to ONE chart of the traded symbol, on the timeframe set in |
//| strategy.timeframe_minutes (e.g. M5). Enable "Allow live trading".|
//| All files live in the terminal's shared Common\Files folder.      |
//|                                                                   |
//| The EA makes no trading decisions. It publishes market/account    |
//| state and executes the open/close commands the engine sends.      |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"

input int MagicNumber   = 20260901;  // must equal live.magic in the config
input int BarsToExport  = 3000;      // closed bars published for warm-up
input int TimerMs       = 500;       // polling interval
input int SlippagePts   = 10;        // must roughly match live.deviation_points

datetime g_lastBarTime = 0;

string Fn(string what) { return "ictb_" + Symbol() + "_" + what; }

int OnInit()
{
   EventSetMillisecondTimer(TimerMs);
   g_lastBarTime = 0;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }

void OnTimer()
{
   RefreshRates();
   ProcessCommands();
   WriteAccount();
   WriteBars();
   WritePositions();
   WriteHistory();
}

// Write to a temp file, then rename, so Python never reads a half-written file.
bool WriteAtomic(string name, string content)
{
   string tmp = name + ".tmp";
   int h = FileOpen(tmp, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE) { Print("ICTBridge: cannot open ", tmp, " err ", GetLastError()); return false; }
   FileWriteString(h, content);
   FileClose(h);
   if(!FileMove(tmp, FILE_COMMON, name, FILE_COMMON | FILE_REWRITE))
   {
      Print("ICTBridge: cannot rename ", tmp, " err ", GetLastError());
      return false;
   }
   return true;
}

string D(double v, int digits) { return DoubleToString(v, digits); }

void WriteAccount()
{
   string s = "";
   s += "symbol=" + Symbol() + "\n";
   s += "timeframe_minutes=" + IntegerToString(Period()) + "\n";
   s += "equity=" + D(AccountEquity(), 2) + "\n";
   s += "demo=" + (IsDemo() ? "1" : "0") + "\n";
   s += "trade_allowed=" + (IsTradeAllowed() ? "1" : "0") + "\n";
   s += "bid=" + D(MarketInfo(Symbol(), MODE_BID), Digits) + "\n";
   s += "ask=" + D(MarketInfo(Symbol(), MODE_ASK), Digits) + "\n";
   s += "tick_value=" + D(MarketInfo(Symbol(), MODE_TICKVALUE), 8) + "\n";
   s += "tick_size=" + D(MarketInfo(Symbol(), MODE_TICKSIZE), 10) + "\n";
   s += "lot_step=" + D(MarketInfo(Symbol(), MODE_LOTSTEP), 4) + "\n";
   s += "min_lot=" + D(MarketInfo(Symbol(), MODE_MINLOT), 4) + "\n";
   s += "max_lot=" + D(MarketInfo(Symbol(), MODE_MAXLOT), 4) + "\n";
   s += "digits=" + IntegerToString(Digits) + "\n";
   s += "gmt_time=" + IntegerToString((long)TimeGMT()) + "\n";
   s += "server_time=" + IntegerToString((long)TimeCurrent()) + "\n";
   WriteAtomic(Fn("account.txt"), s);
}

void WriteBars()
{
   // Only rewrite when a new bar has closed.
   if(Bars < 2 || Time[1] == g_lastBarTime) return;
   g_lastBarTime = Time[1];
   int n = MathMin(BarsToExport, Bars - 1);
   string s = "time,open,high,low,close,volume\n";
   for(int i = n; i >= 1; i--)  // index 0 is the bar still forming
   {
      s += IntegerToString((long)Time[i]) + "," + D(Open[i], Digits) + "," + D(High[i], Digits) + ","
         + D(Low[i], Digits) + "," + D(Close[i], Digits) + "," + IntegerToString((long)Volume[i]) + "\n";
   }
   WriteAtomic(Fn("bars.csv"), s);
}

void WritePositions()
{
   string s = "ticket,type,lots,open_price,sl,tp,open_time\n";
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderMagicNumber() != MagicNumber || OrderSymbol() != Symbol() || OrderType() > OP_SELL) continue;
      s += IntegerToString(OrderTicket()) + "," + IntegerToString(OrderType()) + "," + D(OrderLots(), 2) + ","
         + D(OrderOpenPrice(), Digits) + "," + D(OrderStopLoss(), Digits) + "," + D(OrderTakeProfit(), Digits) + ","
         + IntegerToString((long)OrderOpenTime()) + "\n";
   }
   WriteAtomic(Fn("positions.csv"), s);
}

void WriteHistory()
{
   string s = "ticket,pnl,close_time\n";
   int written = 0;
   for(int i = OrdersHistoryTotal() - 1; i >= 0 && written < 200; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) continue;
      if(OrderMagicNumber() != MagicNumber || OrderSymbol() != Symbol() || OrderType() > OP_SELL) continue;
      double pnl = OrderProfit() + OrderCommission() + OrderSwap();
      s += IntegerToString(OrderTicket()) + "," + D(pnl, 2) + "," + IntegerToString((long)OrderCloseTime()) + "\n";
      written++;
   }
   WriteAtomic(Fn("history.csv"), s);
}

void Respond(string id, string result) { WriteAtomic(Fn("res_" + id + ".txt"), result + "\n"); }

void ProcessCommands()
{
   string found;
   long search = FileFindFirst(Fn("cmd_*.txt"), found, FILE_COMMON);
   if(search == INVALID_HANDLE) return;
   string files[];
   int count = 0;
   do { ArrayResize(files, count + 1); files[count++] = found; } while(FileFindNext(search, found));
   FileFindClose(search);

   for(int f = 0; f < count; f++)
   {
      int h = FileOpen(files[f], FILE_READ | FILE_TXT | FILE_ANSI | FILE_COMMON);
      if(h == INVALID_HANDLE) continue;
      string id = FileReadString(h);
      string action = FileReadString(h);
      string a1 = FileReadString(h), a2 = FileReadString(h), a3 = FileReadString(h), a4 = FileReadString(h), a5 = FileReadString(h);
      FileClose(h);
      // Delete before executing: a crash must never cause the same order twice.
      FileDelete(files[f], FILE_COMMON);

      if(action == "OPEN")       Respond(id, DoOpen((int)StringToInteger(a1), StringToDouble(a2), StringToDouble(a3), StringToDouble(a4), a5));
      else if(action == "CLOSE") Respond(id, DoClose((int)StringToInteger(a1)));
      else                       Respond(id, "ERR unknown action " + action);
   }
}

string DoOpen(int direction, double lots, double sl, double tp, string comment)
{
   if(!IsTradeAllowed()) return "ERR trading not allowed (enable AutoTrading / Allow live trading)";
   RefreshRates();
   int type = direction > 0 ? OP_BUY : OP_SELL;
   double price = direction > 0 ? Ask : Bid;
   sl = NormalizeDouble(sl, Digits);
   tp = NormalizeDouble(tp, Digits);

   int ticket = OrderSend(Symbol(), type, lots, price, SlippagePts, sl, tp, comment, MagicNumber, 0, clrNONE);
   if(ticket > 0) return "OK " + IntegerToString(ticket);

   // Some ECN brokers reject stops on market orders: open bare, then attach them.
   int err = GetLastError();
   RefreshRates();
   price = direction > 0 ? Ask : Bid;
   ticket = OrderSend(Symbol(), type, lots, price, SlippagePts, 0, 0, comment, MagicNumber, 0, clrNONE);
   if(ticket <= 0) return "ERR " + IntegerToString(err) + "/" + IntegerToString(GetLastError()) + " order rejected";
   if(OrderSelect(ticket, SELECT_BY_TICKET) && OrderModify(ticket, OrderOpenPrice(), sl, tp, 0, clrNONE))
      return "OK " + IntegerToString(ticket);

   // Never leave a position without its stop.
   int modErr = GetLastError();
   DoClose(ticket);
   return "ERR " + IntegerToString(modErr) + " could not attach stop loss; position closed";
}

string DoClose(int ticket)
{
   if(!OrderSelect(ticket, SELECT_BY_TICKET, MODE_TRADES) || OrderCloseTime() != 0) return "ERR ticket not open";
   for(int attempt = 0; attempt < 3; attempt++)
   {
      RefreshRates();
      double price = OrderType() == OP_BUY ? Bid : Ask;
      if(OrderClose(ticket, OrderLots(), price, SlippagePts, clrNONE)) return "OK " + IntegerToString(ticket);
      Sleep(300);
   }
   return "ERR " + IntegerToString(GetLastError()) + " close failed";
}
