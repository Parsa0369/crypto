"""Background historical target scan across ten crypto pairs."""
from __future__ import annotations
import ctypes, os, shutil, subprocess, tempfile, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone
from .market_data import MarketDataError, fetch_hourly_klines

SYMBOLS=("BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","LTCUSDT")
HORIZONS=(8,12,18,24)
SOURCE=Path(__file__).resolve().parent.parent/"native"/"deep_scan.cpp"
LOCK=threading.Lock()
STATE={"status":"idle","progress":0,"total":10,"target_pct":5.0,"results":[],"errors":[],"started_at":None,"finished_at":None,"engine":"در انتظار"}
RUNNING=False
ENGINE=None
ENGINE_CHECKED=False
ENGINE_LOCK=threading.Lock()

def load_engine():
 global ENGINE,ENGINE_CHECKED
 with ENGINE_LOCK:
  if ENGINE_CHECKED:return ENGINE
  ENGINE_CHECKED=True
  compiler=shutil.which("g++") or shutil.which("clang++")
  if not compiler:return None
  try:
   out=Path(tempfile.gettempdir())/("cryptopulse_deep_scan"+(".dll" if os.name=="nt" else ".so"))
   cmd=[compiler,"-O3","-std=c++17","-shared"]+([] if os.name=="nt" else ["-fPIC"])+[str(SOURCE),"-o",str(out)]
   subprocess.run(cmd,check=True,capture_output=True,timeout=30)
   lib=ctypes.CDLL(str(out));fn=lib.cryptopulse_target_scan
   fn.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_double),ctypes.c_size_t,ctypes.c_double,ctypes.POINTER(ctypes.c_int),ctypes.c_size_t,ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int)]
   fn.restype=ctypes.c_int;ENGINE=fn;return fn
  except (OSError,subprocess.SubprocessError):return None

def frequencies(candles,target):
 n=len(candles);closes=(ctypes.c_double*n)(*(float(c["close"]) for c in candles));highs=(ctypes.c_double*n)(*(float(c["high"]) for c in candles))
 hs=(ctypes.c_int*4)(*HORIZONS);freq=(ctypes.c_double*4)();counts=(ctypes.c_int*4)();engine=load_engine()
 if engine and engine(closes,highs,n,target,hs,4,freq,counts):return list(freq),list(counts),"C++17"
 vals=[];nums=[]
 for h in HORIZONS:
  sample=max(0,n-h);hits=0
  for i in range(sample):
   goal=float(candles[i]["close"])*(1+target/100)
   if max(float(c["high"]) for c in candles[i+1:i+h+1])>=goal:hits+=1
  vals.append(100*hits/sample if sample else 0);nums.append(sample)
 return vals,nums,"Python fallback"

def scan_one(symbol,target):
 candles=fetch_hourly_klines(symbol,limit=500)
 if len(candles)<60:raise MarketDataError(f"دادهٔ تاریخی کافی برای {symbol} موجود نیست.")
 vals,counts,engine=frequencies(candles,target);last=candles[-1];chart=[{"time":int(c["open_time"]),"price":float(c["close"])} for c in candles[-36:]]
 return ([{"symbol":symbol,"horizon_hours":h,"target_pct":target,"historical_frequency_pct":round(vals[i],2),"sample_count":counts[i],"latest_price":float(last["close"]),"last_candle_time_ms":int(last["open_time"]),"source":last.get("source","Unknown"),"chart":chart} for i,h in enumerate(HORIZONS)],engine)

def run_scan(target):
 global RUNNING
 with LOCK:STATE.update(status="running",progress=0,total=10,target_pct=target,results=[],errors=[],started_at=datetime.now(timezone.utc).isoformat(),finished_at=None,engine="آماده‌سازی موتور")
 try:
  rows_all=[];errors=[];engines=set()
  with ThreadPoolExecutor(max_workers=3,thread_name_prefix="deep-scan") as pool:
   tasks={pool.submit(scan_one,s,target):s for s in SYMBOLS}
   for task in as_completed(tasks):
    try:
     rows,engine=task.result();rows_all.extend(rows);engines.add(engine)
    except Exception as exc:errors.append({"symbol":tasks[task],"error":str(exc)[:220]})
    with LOCK:
     STATE["progress"]+=1;STATE["results"]=sorted(rows_all,key=lambda r:r["historical_frequency_pct"],reverse=True);STATE["errors"]=list(errors);STATE["engine"]=", ".join(sorted(engines)) if engines else "در حال تحلیل"
  with LOCK:STATE["status"]="complete" if rows_all else "error";STATE["engine"]=", ".join(sorted(engines)) if engines else "بدون موتور";STATE["finished_at"]=datetime.now(timezone.utc).isoformat()
 finally:
  with LOCK:RUNNING=False

def start_scan(target):
 global RUNNING
 with LOCK:
  if RUNNING:return False
  RUNNING=True
  threading.Thread(target=run_scan,args=(target,),daemon=True,name="cryptopulse-deep-scan").start()
  return True

def get_scan_state():
 with LOCK:return dict(STATE)
