subscription-management-system

fOR evaluators 
backend runs :
      # Terminal 1
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload

frontend runs :
    # Terminal 2
cd frontend
npm install
npm run dev
