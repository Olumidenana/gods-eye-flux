//+------------------------------------------------------------------+
//| ICTFluxMT5.mq5                                                    |
//| Places ICT Flux signals in your MetaTrader 5 account (e.g. a      |
//| Deriv MT5 demo), so every trade shows up in MT5.                  |
//|                                                                   |
//| Setup (see docs/MT5.md):                                          |
//|  1. Tools > Options > Expert Advisors: tick "Allow WebRequest for |
//|     listed URL" and add https://ictflux.app                       |
//|  2. Attach to ANY one chart (it trades every market itself).      |
//|  3. Turn on the "Algo Trading" button in the toolbar.             |
//| MT5 must stay open on a computer or VPS that stays on.            |
//+------------------------------------------------------------------+
#property copyright "ICT Flux"
#property version   "1.00"

#include <Trade\Trade.mqh>

input string AccessCode       = "";    // your ICT Flux access code
input bool   StrictOnly       = true;  // only ICT strict setups (his markets, killzones, Tue-Fri AM, grade A or better, 2R+)
input string FeedUrl          = "https://ictflux.app/api/scan?format=mt5"; // signal feed
input double RiskPercent      = 1.0;   // risk per trade, % of balance (lost if the stop is hit)
input int    MaxTradesPerDay  = 3;     // new trades per day
input int    MaxOpen          = 2;     // trades open at once
input double DailyLossPercent = 3.0;   // stop for the day after losing this % of the day's start balance
input double MinRR            = 2.0;   // only trades aiming for at least this reward:risk
input string MinGrade         = "B";   // A+, A, B or C
input bool   SplitAtTP1       = true;  // part closes at TP1 (the share set by the style's ICT plan), the rest runs to TP2
input bool   TradeForex       = true;
input bool   TradeMetals      = true;
input bool   TradeIndices     = true;
input bool   TradeCrypto      = false;
input bool   TradeEnergy      = false;
input bool   TradeSynthetics  = true;  // Volatility, Jump, Crash/Boom, Step
input int    FreshMinutes     = 6;     // ignore signals older than this
input int    PollSeconds      = 30;
input int    SlippagePoints   = 50;
input long   Magic            = 20261007;

CTrade trade;
string g_done[];          // "yyyymmdd|signal id|ok" lines, kept in MQL5\Files\ictflux_done.txt
bool   g_warnedWeb = false, g_warnedAlgo = false;
const string DONE_FILE = "ictflux_done.txt";

//------------------------------------------------------------------ helpers
string Today()
{
   MqlDateTime t; TimeToStruct(TimeGMT(), t);
   return StringFormat("%04d%02d%02d", t.year, t.mon, t.day);
}

int GradeRank(string g)
{
   if(g == "A+") return 4;
   if(g == "A")  return 3;
   if(g == "B")  return 2;
   if(g == "C")  return 1;
   return 0;
}

bool ClassAllowed(string c)
{
   if(c == "forex")     return TradeForex;
   if(c == "metal")     return TradeMetals;
   if(c == "index")     return TradeIndices;
   if(c == "crypto")    return TradeCrypto;
   if(c == "energy")    return TradeEnergy;
   if(c == "synthetic") return TradeSynthetics;
   return false;
}

void LoadDone()
{
   ArrayResize(g_done, 0);
   int h = FileOpen(DONE_FILE, FILE_READ | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   while(!FileIsEnding(h))
   {
      string l = FileReadString(h);
      if(StringLen(l) > 0) { int n = ArraySize(g_done); ArrayResize(g_done, n + 1); g_done[n] = l; }
   }
   FileClose(h);
   int keep = 500;  // only the recent history matters
   if(ArraySize(g_done) > keep) { ArrayRemove(g_done, 0, ArraySize(g_done) - keep); SaveDone(); }
}

void SaveDone()
{
   int h = FileOpen(DONE_FILE, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   for(int i = 0; i < ArraySize(g_done); i++) FileWriteString(h, g_done[i] + "\n");
   FileClose(h);
}

void MarkDone(string id, bool ok)
{
   int n = ArraySize(g_done); ArrayResize(g_done, n + 1);
   g_done[n] = Today() + "|" + id + "|" + (ok ? "ok" : "skip");
   SaveDone();
}

bool IsDone(string id)
{
   for(int i = ArraySize(g_done) - 1; i >= 0; i--)
   {
      string f[]; if(StringSplit(g_done[i], '|', f) >= 2 && f[1] == id) return true;
   }
   return false;
}

int TradesToday()
{
   int n = 0; string d = Today();
   for(int i = 0; i < ArraySize(g_done); i++)
   {
      string f[]; if(StringSplit(g_done[i], '|', f) == 3 && f[0] == d && f[2] == "ok") n++;
   }
   return n;
}

// a trade is one single-leg position, or a TP1/TP2 pair counted once
int OpenTrades()
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      long m = PositionGetInteger(POSITION_MAGIC);
      if(m == Magic) n++;
      else if(m == Magic + 1)
      {
         string k = "ICTF_PAIR_" + (string)t;
         if(!GlobalVariableCheck(k) || !PositionSelectByTicket((ulong)GlobalVariableGet(k))) n++;
      }
   }
   return n;
}

bool DailyLossHit()
{
   string k = "ICTF_START_" + Today() + "_" + (string)AccountInfoInteger(ACCOUNT_LOGIN);
   if(!GlobalVariableCheck(k)) GlobalVariableSet(k, AccountInfoDouble(ACCOUNT_BALANCE));
   double start = GlobalVariableGet(k);
   if(start <= 0) return false;
   return (start - AccountInfoDouble(ACCOUNT_EQUITY)) / start * 100.0 >= DailyLossPercent;
}

string ResolveSymbol(string a, string b)
{
   if(StringLen(a) > 0 && SymbolSelect(a, true)) return a;
   if(StringLen(b) > 0 && SymbolSelect(b, true)) return b;
   return "";
}

double NormLots(string sym, double lots)
{
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double mx   = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(step <= 0) step = 0.01;
   lots = MathFloor(lots / step + 1e-9) * step;
   return MathMin(lots, mx);
}

// After TP1 closes the first half, move the second half's stop to its entry (TP-04)
void ManageBreakeven()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetInteger(POSITION_MAGIC) != Magic + 1) continue;
      string k = "ICTF_PAIR_" + (string)t;
      if(!GlobalVariableCheck(k)) continue;
      ulong first = (ulong)GlobalVariableGet(k);
      if(PositionSelectByTicket(first)) continue;  // TP1 leg still open
      if(!PositionSelectByTicket(t)) continue;
      string sym = PositionGetString(POSITION_SYMBOL);
      double open = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL), tp = PositionGetDouble(POSITION_TP);
      bool buy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      if((buy && sl >= open) || (!buy && sl > 0 && sl <= open)) { GlobalVariableDel(k); continue; }
      if(trade.PositionModify(t, NormalizeDouble(open, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS)), tp))
      {
         Print("ICT Flux: TP1 hit, stop moved to entry on ", sym);
         GlobalVariableDel(k);
      }
   }
}

// ICT stop management on every ICT Flux position (SL-04, SL-05): halfway to the position's
// target the stop's risk is cut by 25% (intraday and swing plans), and at 75% it goes to entry.
void ManageStops()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      long m = PositionGetInteger(POSITION_MAGIC);
      if(m != Magic && m != Magic + 1) continue;
      string k = "ICTF_SL0_" + (string)t;
      if(!GlobalVariableCheck(k)) continue;
      string sym = PositionGetString(POSITION_SYMBOL);
      double open = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL), tp = PositionGetDouble(POSITION_TP);
      double sl0 = GlobalVariableGet(k);
      bool buy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY, trim = GlobalVariableCheck("ICTF_TRIM_" + (string)t);
      if(tp <= 0 || tp == open) continue;
      double px = buy ? SymbolInfoDouble(sym, SYMBOL_BID) : SymbolInfoDouble(sym, SYMBOL_ASK);
      double progress = buy ? (px - open) / (tp - open) : (open - px) / (open - tp);
      double want = sl, d = buy ? 1 : -1;
      if(progress >= 0.75) want = open;
      else if(trim && progress >= 0.5) want = open - d * 0.75 * MathAbs(open - sl0);
      else continue;
      want = NormalizeDouble(want, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS));
      if((buy && want > sl) || (!buy && (sl == 0 || want < sl)))
         if(trade.PositionModify(t, want, tp)) Print("ICT Flux: ", sym, progress >= 0.75 ? " 75% of the way, stop to entry" : " halfway, stop risk cut by 25%");
   }
}

void Remember(ulong ticket, double sl0, bool trim)
{
   GlobalVariableSet("ICTF_SL0_" + (string)ticket, sl0);
   if(trim) GlobalVariableSet("ICTF_TRIM_" + (string)ticket, 1);
}

//------------------------------------------------------------------ one signal
// fields: id|cls|mt5 symbol|label|buy/sell|entry|stop|tp1|target|rr|grade|epoch|tf|share off at TP1
void Consider(string &f[])
{
   string id = f[0], cls = f[1];
   if(IsDone(id)) return;
   bool buy = f[4] == "buy";
   double stop = StringToDouble(f[6]), tp1 = StringToDouble(f[7]), target = StringToDouble(f[8]), rr = StringToDouble(f[9]);
   long age = (long)TimeGMT() - StringToInteger(f[11]);
   int tf = (int)StringToInteger(f[12]);
   if(age > (long)MathMax(FreshMinutes, 1.2 * tf) * 60) return;  // too old: leave it, it will just age out
   if(!ClassAllowed(cls) || rr < MinRR || GradeRank(f[10]) < GradeRank(MinGrade)) { MarkDone(id, false); return; }

   if(TradesToday() >= MaxTradesPerDay) { Print("ICT Flux: skipped ", f[3], " - max trades per day reached"); MarkDone(id, false); return; }
   if(OpenTrades() >= MaxOpen)          { Print("ICT Flux: skipped ", f[3], " - max open trades reached"); MarkDone(id, false); return; }
   if(DailyLossHit())                   { Print("ICT Flux: skipped ", f[3], " - daily loss limit reached"); MarkDone(id, false); return; }

   string sym = ResolveSymbol(f[2], f[3]);
   if(sym == "") { Print("ICT Flux: skipped ", f[3], " - this MT5 account has no such symbol"); MarkDone(id, false); return; }

   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   double price = buy ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID);
   if(price <= 0) { Print("ICT Flux: no price for ", sym, ", will retry"); return; }
   double minDist = (SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) + 2) * point;
   // the market must still be between the stop and the target
   if((buy && (price - stop < minDist || target - price < minDist)) || (!buy && (stop - price < minDist || price - target < minDist)))
   { Print("ICT Flux: skipped ", sym, " - price already moved past the stop or target"); MarkDone(id, false); return; }

   double loss1 = 0;  // money lost by 1 lot from here to the stop
   if(!OrderCalcProfit(buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, sym, 1.0, price, stop, loss1) || loss1 >= 0)
   { Print("ICT Flux: could not size ", sym, ", will retry"); return; }
   double risk = AccountInfoDouble(ACCOUNT_BALANCE) * RiskPercent / 100.0;
   double lots = NormLots(sym, risk / -loss1);
   double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   if(lots < vmin)
   { Print("ICT Flux: skipped ", sym, " - the smallest lot (", vmin, ") risks more than ", RiskPercent, "%"); MarkDone(id, false); return; }

   bool tp1ok = tp1 > 0 && (buy ? (tp1 - price >= minDist && tp1 < target) : (price - tp1 >= minDist && tp1 > target));
   double part = ArraySize(f) > 13 ? StringToDouble(f[13]) : 0.5;  // share off at TP1, from the style's ICT plan
   double lots1 = NormLots(sym, lots * part), lots2 = NormLots(sym, lots - lots1);
   bool split = SplitAtTP1 && tp1ok && part > 0 && lots1 >= vmin && lots2 >= vmin;
   bool trim = tf >= 5 && tf <= 60;  // SL-04 belongs to the intraday and swing plans
   stop = NormalizeDouble(stop, digits); target = NormalizeDouble(target, digits); tp1 = NormalizeDouble(tp1, digits);
   string cmt = "ICTF " + StringSubstr(id, 0, 26);

   trade.SetTypeFillingBySymbol(sym);
   bool ok;
   if(split)
   {
      trade.SetExpertMagicNumber(Magic);
      ok = buy ? trade.Buy(lots1, sym, 0, stop, tp1, cmt) : trade.Sell(lots1, sym, 0, stop, tp1, cmt);
      ulong t1 = ok ? trade.ResultOrder() : 0;
      if(ok)
      {
         trade.SetExpertMagicNumber(Magic + 1);
         bool ok2 = buy ? trade.Buy(lots2, sym, 0, stop, target, cmt) : trade.Sell(lots2, sym, 0, stop, target, cmt);
         if(ok2) { GlobalVariableSet("ICTF_PAIR_" + (string)trade.ResultOrder(), (double)t1); Remember(trade.ResultOrder(), stop, trim); }
         else Print("ICT Flux: TP2 part failed on ", sym, ": ", trade.ResultRetcodeDescription());
      }
   }
   else
   {
      trade.SetExpertMagicNumber(Magic);
      ok = buy ? trade.Buy(lots, sym, 0, stop, target, cmt) : trade.Sell(lots, sym, 0, stop, target, cmt);
      if(ok) Remember(trade.ResultOrder(), stop, trim);
   }
   if(ok) Print("ICT Flux: ", (buy ? "BUY " : "SELL "), sym, " ", (split ? lots1 + lots2 : lots), " lots, SL ", stop, (split ? ", TP1 " + DoubleToString(tp1, digits) : ""), ", TP ", target);
   else   Print("ICT Flux: order failed on ", sym, ": ", trade.ResultRetcodeDescription());
   MarkDone(id, ok);
}

//------------------------------------------------------------------ events
int OnInit()
{
   trade.SetDeviationInPoints(SlippagePoints);
   LoadDone();
   EventSetTimer(MathMax(PollSeconds, 10));
   Print("ICT Flux: started on account ", AccountInfoInteger(ACCOUNT_LOGIN), (AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_DEMO ? " (demo)" : " (REAL MONEY)"),
         ", risk ", RiskPercent, "% per trade");
   OnTimer();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }

void OnTimer()
{
   ManageBreakeven();
   ManageStops();
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      if(!g_warnedAlgo) Print("ICT Flux: turn on the 'Algo Trading' button in the toolbar, and tick 'Allow Algo Trading' in the robot's settings.");
      g_warnedAlgo = true; return;
   }
   g_warnedAlgo = false;

   char body[], res[]; string hdr;
   ResetLastError();
   string url = FeedUrl + (StringLen(AccessCode) > 0 ? "&code=" + AccessCode : "") + (StrictOnly ? "&strict=1" : "");
   int code = WebRequest("GET", url, "", 60000, body, res, hdr);
   if(code == -1)
   {
      if(!g_warnedWeb) Print("ICT Flux: cannot reach the feed (error ", GetLastError(), "). Tools > Options > Expert Advisors: tick 'Allow WebRequest' and add https://ictflux.app");
      g_warnedWeb = true; return;
   }
   g_warnedWeb = false;
   if(code == 401) { Print("ICT Flux: access refused. Put your ICT Flux access code in the robot's Inputs (AccessCode). ", CharArrayToString(res, 0, WHOLE_ARRAY, CP_UTF8)); return; }
   if(code != 200) { Print("ICT Flux: feed returned HTTP ", code, ", will retry"); return; }

   string lines[];
   int n = StringSplit(CharArrayToString(res, 0, WHOLE_ARRAY, CP_UTF8), '\n', lines);
   if(n < 1 || StringFind(lines[0], "ICTFLUX1|") != 0) { Print("ICT Flux: unexpected feed reply"); return; }
   for(int i = 1; i < n; i++)
   {
      string f[];
      if(StringSplit(lines[i], '|', f) >= 13) Consider(f);
   }
}
//+------------------------------------------------------------------+
