# Distributor Stock Rebate GUI

A desktop app (PySide6) that calculates monthly stock rebates for Walton and Marcel distributors. It pulls stock, lifting and receivable data from the data lake, removes parties that don't qualify, and works out the rebate for the rest.

## Key separation

- **Exclusion Conditions** decides eligibility and records every exclusion reason.
- **Rebate Engine** only calculates rebate for eligible parties.
- Exclusion thresholds are editable in the **Excluded Parties** tab.
- Rebate percentage tiers are editable in the **Rebate** tab.
- Every result is retained as a pandas DataFrame and displayed in tabs.
- Excluded parties can be exported to Excel.
- The Final result is automatically saved in the path output folder.


## How to Run

1. Create a Python 3.13+ virtual environment.
2. Activate that environment and then run `python -m pip install -r requirements.txt` in the terminal.
3. Run: `python app.py`

This application executes database work in a worker thread so the GUI stays responsive in the main thread.

## Workflow

Dashboard -> Entered Stock -> Party Info / Duplicate Check -> Party Lifting -> Party Receivable
-> Exclusion Conditions Validation -> Excluded Parties review -> Rebate Engine -> High-stock validation -> Results.

1. Fetches entered stock, party info, party lifting and party receivable for the chosen month.
2. Matches each party's stock against its lifting by item and model, and calculates the effective stock value.
3. Applies the exclusion rules and records the reason for every excluded party.
4. Calculates the rebate for eligible parties using the rebate tiers.
5. Saves the results as CSV files.

## Architecture

1. Firstly, when in the terminal python app.py is entered it goes to that app.py file and from there **main_window.py** file is redirected where all the execution calls are located. Since I have used pandas dataframe pySide6 python's default framework doesn't take or understand the table from pd.Dataframe, which is why DFModel is used as an adapter.
2. Then it hits basically the **MainWindow** class **run_next_step** and **run_all** function which takes it to the **workflow.py** file which is the heart of this project and it runs all the execution logics and processes there. 
3. The **exclusion_engine** and **rebate_engine** files in the business folder holds all the conditions.
4. **queries.py** file holds all the queries and **data_service.py** file holds the function execution calls based on the queries.
5. The **widgets.py**, **icons.py** & **styles.py** files all are working for the colorful UI with icons here. They are not related to the calculation logics. 