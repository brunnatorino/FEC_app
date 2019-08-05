Package for automating the generation of the French auditing file FEC with an excel file output. 
Uses Gooey for a user-friendly interface, translates to French and maps accounts/suppliers/journalcodes

REQUIREMENTS:

Change your columns to the exact name columns considering lower/upper cases and spaces to the French FEC standards (ex: JournalCode)
Use Debits and Credits format (with column names: Debit and Credit) 


Please be aware you need to create master files for your specific:
1) Account Numbers corresponding to PCG French accounts (name the file mapping-accounts.xlsx)
	a) Name the Columns: G/L Account # (for the company's account numbers)
	b) FrMap (for the corresponding French standard)
	c) FEC Compliant (for the corresponding French Account Name)
2) Vendor numbers to vendor names (name the file Vendors.xlsx)
	a) Name the Columns: No (Vendor Number)
	b) Name (Vendor Name)
3) Journal Codes to Journal Names in French (name the file mapping-journal.xlsx)
	a) JournalCode (for the journals codes)
	b) JournalLib (for the corresponding names in French)
	
