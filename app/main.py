from fastapi import FastAPI,UploadFile,File,Depends,HTTPException
from sqlalchemy import create_engine,Column,Integer,String,Float,func
from sqlalchemy.orm import declarative_base,sessionmaker,Session
from apscheduler.schedulers.background import BackgroundScheduler
import csv,io
engine=create_engine('sqlite:///./integration.db',connect_args={'check_same_thread':False}); Base=declarative_base(); SessionLocal=sessionmaker(bind=engine)
class Record(Base):
 __tablename__='records'; id=Column(Integer,primary_key=True); customer=Column(String,index=True); amount=Column(Float); source=Column(String); status=Column(String,default='valid')
Base.metadata.create_all(engine)
def db():
 s=SessionLocal();
 try: yield s
 finally:s.close()
def normalize(row):
 customer=(row.get('customer') or row.get('customer_name') or '').strip(); raw=(row.get('amount') or row.get('value') or '').strip(); return customer,float(raw)
def report_job():
 with SessionLocal() as s: print('scheduled report: records=',s.query(Record).count())
scheduler=BackgroundScheduler(); scheduler.add_job(report_job,'interval',hours=24); scheduler.start()
app=FastAPI(title='Data Integration & Reporting Backend')
@app.get('/health')
def health(): return {'status':'ok'}
@app.post('/ingest/csv')
async def ingest(file:UploadFile=File(...),s:Session=Depends(db)):
 text=(await file.read()).decode('utf-8'); reader=csv.DictReader(io.StringIO(text)); added=0; rejected=0
 for row in reader:
  try:
   customer,amount=normalize(row)
   if not customer or amount<0: raise ValueError()
   s.add(Record(customer=customer,amount=amount,source=file.filename)); added+=1
  except Exception: rejected+=1
 s.commit(); return {'inserted':added,'rejected':rejected}
@app.get('/analytics/summary')
def summary(s:Session=Depends(db)):
 total,count=s.query(func.coalesce(func.sum(Record.amount),0),func.count(Record.id)).one(); return {'total_amount':float(total),'record_count':count}
@app.get('/analytics/by-customer')
def by_customer(s:Session=Depends(db)):
 rows=s.query(Record.customer,func.sum(Record.amount).label('total')).group_by(Record.customer).all(); return [{'customer':c,'total':float(t)} for c,t in rows]
