import pandas as pd
from gooey import Gooey, GooeyParser
import numpy as np
import xlsxwriter
import xlrd
import re



@Gooey(program_name="FEC FILE FOR FRANCE",default_size=(710, 700),navigation='TABBED', header_bg_color = '#48a7fa')

def parse_args():
    parser = GooeyParser()

    parser.add_argument('Financial_Year',
                        action='store',
                        help="Financial Year in format YYYY")

    FilesGL = parser.add_argument_group('GL Posted Items')
    
    FilesGL.add_argument('GL',
                        action='store',
                        widget='FileChooser',
                        help="Excel File From SAP G/L View: Normal Items")

    FileNOTE = parser.add_argument_group('Entry View Parked Items')
    FileNOTE.add_argument('Parked',
                        action='store',
                        widget='FileChooser',
                        help="Excel File From SAP Entry View: Only Parked and Noted Items")
    FileCarry = parser.add_argument_group('Carryforwards File')
    FileCarry.add_argument('Carryforwards',
                        action='store',
                        widget='FileChooser',
                        help="Excel File From SAP Entry View: Carryforwards")
    

    choose = parser.add_argument_group('FEC Name - Excel')
    choose.add_argument('Excel_File',
                        action='store',
                        help="File name with .xlsx in the end. Standard for FEC is 533080222FECYYYYMMDD",
                         gooey_options={
                             'validator': {
                                 'test': 'user_input.endswith(".xlsx") == True',
                                 'message': 'Must contain .xlsx at the end!'
                                 }
                             })
    choose1 = parser.add_argument_group('FEC Name - Text')
    choose1.add_argument('Text_File',
                    action='store',
                    help="File name with .txt in the end. Standard for FEC is 533080222FECYYYYMMDD",
                     gooey_options={
                         'validator': {
                             'test': 'user_input.endswith(".txt") == True',
                             'message': 'Must contain .txt at the end!'
                             }
                         })

    args = parser.parse_args()
    return args

def carry(gl):
    accounts = pd.read_excel("mapping-accounts.xlsx")
    gl = pd.read_excel(gl)
    gl['JournalCode'] = 'AN'
    gl['JournalLib'] = 'A NOVEAU' 
    gl['EcritureNum'] = 'AN000001'
    gl['EcritureDate'] = '2018-10-28'
    gl['EcritureDate'] = pd.to_datetime(gl['EcritureDate'], errors='coerce')
    gl['CompteNum'] = gl['G/L acct']
    gl['CompteLib'] = gl['G/L acct']
    gl['CompAuxLib'] = ''
    gl['PieceRef'] = ''
    gl['EcritureLib'] = ''
    gl['Amount'] = gl['Balance']
    gl['MontantDevise'] = ''
    gl['ldevise'] = ''
    gl['PieceDate'] = gl['EcritureDate']
    gl['ValidDate'] = gl['EcritureDate']
    gl['EcritureLet'] = ''
    gl['DateLet'] = ''

    gl = gl.dropna(subset=['Amount']) 

    gl.loc[gl["Amount"] < 0 ,'Credit'] = gl['Amount']
    gl.loc[gl["Amount"] > 0 ,'Debit'] = gl['Amount']

    gl.loc[gl["Debit"].isnull() ,'Debit'] = 0
    gl.loc[gl["Credit"].isnull() ,'Credit'] = 0

    del gl['Amount']

    accounts1 = accounts[['G/L Account #','FrMap']] 
    accounts2 = accounts[['G/L Account #','FEC Compliant']]

    accounts1 = accounts1.set_index('G/L Account #').to_dict()['FrMap']
    accounts2 = accounts2.set_index('G/L Account #').to_dict()['FEC Compliant']

    gl['CompteLib'] = gl['CompteLib'].replace(accounts2)
    gl['CompteNum'] = (gl['CompteNum'].map(accounts1).astype('Int64').astype(str) + gl['CompteNum'].astype(str))
    gl['CompteNum'] = gl['CompteNum'].str.replace('\.0$', '')

    writer = pd.ExcelWriter('file_carryforwards.xlsx',
                            engine='xlsxwriter',
                            datetime_format='yyyymmdd',
                            date_format='yyyymmdd')

    gl.to_excel(writer, index = False,sheet_name = ('Carry'), columns =['JournalCode','JournalLib','EcritureNum','EcritureDate','CompteNum',
                                                                'CompteLib','CompAuxNum','CompAuxLib','PieceRef','PieceDate','EcritureLib',
                                                                'Debit','Credit','EcritureLet','DateLet','ValidDate','MontantDevise','ldevise'])


    workbook  = writer.book
    worksheet = writer.sheets['Carry']
    worksheet.set_column('A:AV', 40)
    writer.save()

    return gl

        

def combine(file, file2, carry):
    gl_df = pd.read_excel(file)
    parked_df = pd.read_excel(file2)
    
    numbers = gl_df['Document Number'].tolist()

    gl = gl_df.append(parked_df[~parked_df['Document Number'].isin(numbers)])
    gl = gl.reset_index()
    carry = carry.append(gl)
    
    return gl



def transform(gl):
    
    gl['JournalCode'] = gl['Document Type']
    gl['JournalLib'] = gl['Document Header Text']
    gl['EcritureNum'] = gl['Document Number']
    gl['EcritureDate'] = gl['Posting Date']
    gl['CompteNum'] = gl['G/L Account']
    gl['CompteLib'] = gl['G/L Account']
    gl['CompAuxLib'] = gl['Offsetting acct no.']
    gl['PieceRef'] = gl['Reference']
    gl['EcritureLib'] = gl['Text']
    gl['Amount'] = gl['Amount in local currency']
    gl['MontantDevise'] = ''
    gl['ldevise'] = ''
    gl['PieceDate'] = gl['Document Date']
    gl['ValidDate'] = gl['Entry Date']
    gl['EcritureLet'] = ''
    gl['DateLet'] = ''

    
    gl = gl.dropna(subset=['Amount']) 

    gl.loc[gl["Amount"] < 0 ,'Credit'] = gl['Amount']
    gl.loc[gl["Amount"] > 0 ,'Debit'] = gl['Amount']

    gl.loc[gl["Debit"].isnull() ,'Debit'] = 0
    gl.loc[gl["Credit"].isnull() ,'Credit'] = 0

    del gl['Amount']
    del gl['Amount in local currency']

    accounts = pd.read_excel("mapping-accounts.xlsx")
    accounts1 = accounts[['G/L Account #','FrMap']] 
    accounts2 = accounts[['G/L Account #','FEC Compliant']]

    accounts1 = accounts1.set_index('G/L Account #').to_dict()['FrMap']
    accounts2 = accounts2.set_index('G/L Account #').to_dict()['FEC Compliant']

    gl['CompteLib'] = gl['CompteLib'].replace(accounts2)
    gl['CompteNum'] = (gl['CompteNum'].map(accounts1).astype('Int64').astype(str) + gl['CompteNum'].astype(str))
    gl['CompteNum'] = gl['CompteNum'].str.replace('\.0$', '')

    journals = pd.read_excel("test128.xlsx")
    codes = pd.read_excel('mapping-journal.xlsx')

    journals = journals.set_index('DocHeader').to_dict()['JournalLib_FR']
    codes = codes.set_index('JournalCode').to_dict()["JournalLib_FR"]

    gl.loc[gl["JournalLib"].isnull(),'JournalLib'] = gl["JournalCode"].map(str)
    gl['JournalLib'] = gl['JournalLib'].replace(journals)
    gl['JournalLib'] = gl['JournalLib'].replace(codes)
    vendors = pd.read_excel("Vendors1.xlsx")
    vendors = vendors.set_index('No').to_dict()['Name']
    gl['CompAuxLib'] = gl['CompAuxLib'].map(vendors)
    gl['CompAuxNum'] = "F" + gl['CompAuxLib']
    gl['EcritureLib'] = gl["EcritureLib"].str.replace(" + "," ")

    gl.loc[(~gl.CompAuxLib.isnull()) & (gl["EcritureLib"].isnull()),'EcritureLib'] = gl['JournalLib'].map(str) + " de " + gl['CompAuxLib'].map(str)
    gl.loc[(gl.CompAuxLib.isnull()) & (gl["EcritureLib"].isnull()),'EcritureLib'] = gl['JournalLib'].map(str) + gl['EcritureNum'].map(str)



    return gl


def translate(gl):
    journals = pd.read_excel("test128.xlsx")
    codes = pd.read_excel('mapping-journal.xlsx')

    journals = journals.set_index('DocHeader').to_dict()['JournalLib_FR']
    codes = codes.set_index('JournalCode').to_dict()["JournalLib_FR"]
    
    mapping_Valuation = {"Valuation on": "Évaluation sur","Valuation on Reverse":"Évaluation sur Contre Passation",
                         "Reverse Posting":"Contre-Passation d'Ecriture - Conversion de devise sur",
                         "Translation Using":"Conversion de devise sur"}
    mapping_AA = {"Reclass from": "Reclassification de", "reclass from": "Reclassification de", "ZEE MEDIA":"ZEE MEDIA Campaignes Numériques", "TRAINING CONTRI. ER JANUARY '19":"FORMATION CONTRI. ER JANVIER' 19",
                  "TAX FEES":"Taxes","SOCIAL SECURITY: URSSAF":"SÉCURITÉ SOCIALE: URSSAF","SOCIAL SECURITY: TRAINING CONTRIBUTIONS":"SÉCURITÉ SOCIALE: CONTRIBUTIONS À LA FORMATION",
                  "SOCIAL SECURITY: APPRENTICESHIP CONTRIBU":"SÉCURITÉ SOCIALE: CONTRIBUTION À L’APPRENTISSAGE","RSM":"SERVICES DE PAIE RSM EF18","RSA":"SERVICES DE PAIE RSA OCT-JAN",
                  "PRIVATE HEALTH":"SANTÉ PRIVÉE: ASSURANCE MÉDICALE-AXA/","PENSION: PENSION CONTRIBUTIONS - REUNICA":"PENSION: COTISATIONS DE RETRAITE-REUNICA","PENSION: LIFE & DISABILITY INSURANCE - R":"PENSION: ASSURANCE VIE & INVALIDITÉ-R", 
                  "PENSION JANUARY '19":"PENSION JANVIER '19",
                  "ON CALL JANUARY '19":"Disponible Janvier'19",
                  "NRE + PROJECT INITIATION FEES":"NRE + FRAIS D’INITIATION AU PROJET (PO 750003","NET PAY JANUARY '19":"Payeante Janvier'19","JANUARY'19":"JANVIER'19",
                  "LUNCH VOUCHER- WITHHOLDING":"BON DÉJEUNER-RETENUE","HOLIDAY BONUS ACCRUAL FY18/19":"CUMUL DES PRIMES DE VACANCES EF18/19",
                  "GROSS SALARY JANUARY '19":"SALAIRE BRUT JANVIER' 19","EMEA ACCRUAL P8FY19":"P8FY19 D’ACCUMULATION EMEA","COMMISSION RE-ACCRUAL":"COMMISSION RÉ-ACCUMULATION",
                  "COMMISSION ACCRUAL":"COMMISSION D’ACCUMULATION","MARCH":"MARS","MAY":"MAI","APRIL":"AVRIL","AUDIT FEES":"HONORAIRES D’AUDIT",
                  "UNSUBMITTED_UNPOSTED BOA ACCRUAL":"Accumulation BOA non soumise non exposée","UNASSIGNED CREDITCARD BOA ACCRUAL":"NON ASSIGNÉ CREDITCARD BOA ACCUMULATION ",
                  "EMEA ACCRUAL":"ACCUMULATION EMEA","Exhibit Expenses":"Frais d'exposition","Hotel Tax":"Taxe hôtelière","Company Events":"Événements d'entreprise",
                  "Public Transport":"Transport public", "Agency Booking Fees":"Frais de réservation d'agence","Working Meals (Employees Only)":"Repas de travail (employés seulement)",
                  "Airfare":"Billet d'avion","Office Supplies":"Fournitures de bureau","Tolls":"Péages",
                  "write off difference see e-mail attached":"radiation de la différence voir e-mail ci-joint",
                 "Manual P/ment and double payment to be deduct":"P/ment manuel et double paiement à déduire","FX DIFFERENCE ON RSU":"DIFFERENCE FX SUR RSU",
                 "DEFINED BENEFIT LIABILITY-TRUE UP":"RESPONSABILITÉ À PRESTATIONS DÉTERMINÉES-TRUE UP","EXTRA RELEASE FOR STORAGE REVERSED":"EXTRA LIBERATION POUR STOCKAGE CONTREPASSATION",
                 "RECLASS BANK CHARGES TO CORRECT COST CEN":"RECLASSER LES FRAIS BANCAIRES POUR CORRIGER","PAYROLL INCOME TAXES":"IMPÔTS SUR LES SALAIRES",
                  "TRAINING TAX TRUE UP":"TAXE DE FORMATION", "FX DIFFERENCE ON STOCK OPTION EXERCISES":"FX DIFFERENCE SUR LES EXERCICES D'OPTIONS STOCK",
                  "Airline Frais":"Frais de Transport Aérien","Agency Booking Fees":"Frais de Réservation d'Agence","Computer Supplies":"Fournitures informatiques",
                 "AUDIT FEES":"FRAIS D'AUDIT", "HOLIDAY BONUS ACCRUAL ":"ACCUMULATION DE BONUS DE VACANCES","TAX FEES":"FRAIS D'IMPÔT",
                  "SOCIAL SECURITY: APPRENTICESHIP CONTRIBU":"SÉCURITÉ SOCIALE: CONTRIBUITION À L’APPRENTISSAGE",
                  "SOCIAL SECURITY: TRAINING CONTRIBUTIONS":"SÉCURITÉ SOCIALE: CONTRIBUTIONS À LA FORMATION", "TRAVEL COST":"FRAIS DE VOYAGE", "HOUSING TAX":"TAXE SUR LE LOGEMENT", 
                 "PAYROLL INCOME TAXES":"IMPÔTS SUR LE REVENU DE LA PAIE","INCOME TAX-PAS":"IMPÔT SUR LE REVENU-PAS", "IC SETTLEMENT":"Règlement Interentreprises",
                 "VACATION TAKEN":"VACANCES PRISES", "SOCIAL SECURITY: APPR. CONTR.":"SÉCURITÉ SOCIALE: CONTRIBUTION À L’APPRENTISSAGE", 
                  "POST OF AVRIL DEC IN CORRECT SIGN":"CORRECTION D'ECRITURE AVRIL DEC"}



    gl = gl.replace({"EcritureLib":mapping_Valuation}, regex=True)
    gl = gl.replace({"EcritureLib":mapping_AA}, regex=True)

    gl['EcritureLib'] = gl["EcritureLib"].str.replace('COST-PLUS', 'Revient Majoré')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('PRITVAE HEALTH: MEDICAL INSURANCE', 'SANTÉ PRIVÉE: ASSURANCE MÉDICALE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('MEDICAL INSURANCE', 'ASSURANCE MÉDICALE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('UNASSIGNED', 'NON ATTRIBUÉ')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('Payout', 'Paiement')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('FRINGE COST', 'COÛT MARGINAL')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('PROJECT INITIATION', 'LANCEMENT DU PROJET')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('ACCRUAL', 'ACCUMULATION')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('CREDITCARD', 'CARTE DE CRÉDIT')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('ACCR ', 'ACCUM ')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('VAT ', 'TVA ')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('SOCIAL SECURITY ', 'SÉCURITÉ SOCIALE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('SEPTEMBER', 'SEPT')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('TAXBACK', 'Reboursement')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('REPORT', '')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Reverse Posting", "Contre Passation d'Ecriture")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("BASE RENT", "Location Base")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Rent ", "Location ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("RENT ", "Location ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("CLEARING", "compensation ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("clearing", "compensation ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("BILLING CHARGES", "FRAIS DE FACTURATION ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("UNPAID", "NON PAYÉ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("PROPERTY TAX", "IMPÔT FONCIER ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Trans. Using", "Conversion sur")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("SALARIES", "Salaires")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Refund", "Remboursement")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("REFUND", "Remboursement")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("no invoice", "pas de facture")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("COST-PLUS SERVICE REVENUE", "Revenus de service Revient Majoré")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("SETTLEMENT", "RÈGLEMENT ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("PURCHASE", "ACHAT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("NON-CP SETTLE", "RÈGLEMENT NON-CP")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("PAID ", " Payé ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("FEES ", "Frais")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("January", "Janvier")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("February", "Février")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("March", "Mars")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("April", "Avril")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("May", "Mai")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("June", "Juin")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("July", "Juillet")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("September", "Septembre")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Aug.", "Août")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("JANUARY", "Janvier")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("FEBRUARY", "Février")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("MARCH", "Mars")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("APRIL", "Avril")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("MAY", "Mai")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("JUNE", "Juin")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("JULY", "Juillet")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("SEPTEMBER", "Septembre")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("AUGUST.", "Août")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("NOVEMBER.", "Novembre")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("DECEMBER.", "Décembre")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("December", "Décembre")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Feb.", "Fév.")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Mar.", "Mars")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Apr.", "Avril")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Aug.", "Août")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Aug.", "Août")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Reverse ", "Contre-passation ")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("INTEREST CHARGE", "CHARGE D'INTÉRÊT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("-SICK LEAVE PAY", "-Paiement congé maladie")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("RECLASSEMENTIFICATION", "RECLASSIFICATION")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("INSTALMENT", "VERSEMENT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("FIRST", "1ere")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("FINE LATE PAY.", "Amende pour retard de paiement")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("-PATERNITY PAY", "Indemnités de paternité")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("SOCIAL SECURITY:", "SÉCURITÉ SOCIALE:")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Trip from", "Voyage de:")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace(" To ", " à")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Shipping", "Livraison")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("VOXEET INTEGRATION COSTS", "COÛTS D'INTÉGRATION DE VOXEET")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("INCOME TAX", "IMPÔT SUR LE REVENU")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('Rideshare', 'Covoiturage')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('Travel Meals', 'Repas de Travail')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('Fees', 'Frais')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('Phone', 'Téléphone')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Books", "Abonnements")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Subcriptions", "Location Base")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Meals", "Repas")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Entertainment", "divertissement ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Third Party", "tiers ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Training Fees", "Frais d0 Formation")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Conferences/Tradeshows Registratio", "Conférences/Tradeshows Enregistrement")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("FOR", "POUR")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("ROUNDING", "ARRONDISSEMENT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("STORAGE", "STOCKAGE")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("VACATION ACCURAL", "Vacances Accumulées")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("RECEIVABLE ", "Recevables")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("AFTER PAYOUT ", "APRÈS PAIEMENT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("CLEAN UP ", "APUREMENT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("EMPLOYEE TRAVEL INSUR ", "ASSURANCE DE VOYAGE DES EMPLOYÉS")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("CORRECTION OF", "CORRECTION DE")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("TAXES PAYROLL", "IMPÔTS SUR LA MASSE SALARIALE")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("ACCOUNT", "COMPTE")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("TAX", "Impôt")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("life disab", "Incapacité de vie")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("HOUSING TAX","TAXE D'HABITATION")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("GROSS SALARY","SALAIRE BRUT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Cleaning Services","Nettoyage")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Freight","Fret")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Membership","adhésion")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Air cooling Maintenance","Entretien de refroidissement de l'air")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Power on Demand Platform","Plateforme d'energie à la demande")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Sanitaire room installation"," Installation de la salle sanitaire")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("subscription","abonnement")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Coffee supplies "," Fournitures de café")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Duty and Tax ","Devoir et fiscalité")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Electricity ","Electricité ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Lunch vouchers  ","Bons déjeuner")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Security monitoring","Surveillance de la sécurité")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Water", "L'EAU")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Statutory Audit", "Audit statutaire")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace(" Meeting room screen installation", "Installation de l'écran de la salle de réunion")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Water", "L'EAU")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Water", "L'EAU")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Tax Credit FY 2016", "Crédit d'impôt Exercice 2016")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Bank of America Merill Lynch-T&E statement","Déclaration de Merill Lynch")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("English Translation", "Traduction anglaise")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Office Rent", "Location de Bureau")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Annual Electrical Verification", "Vérification électrique annuelle ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Health costs ", "Coûts santé")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Unlimited-receipt and policy audit", "Vérification illimitée des reçus et audites")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Water fountain ", "Fontaine d'eau")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Quartely control visit", "Visite de contrôle trimestrielle")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Fire extinguishers annual check", "Vérification annuelle des extincteurs")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("showroom rent", "location de salle d'exposition")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("AND ACTUAL RECEIV","ET RECETTES RÉELLES")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("FILING","DÉPÔT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("ORDERS","ORDRES")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("EXCLUDED -DUMMY CREDIT","EXCLU")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("RELARING TO","RELATIF À")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("CLEAN UP-","APUREMENT-")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("2ND INSTALLEMENT","2ème versement")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("DOUBLE PAYMENT","DOUBLE PAIEMENT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("CLEAN UP-","APUREMENT-")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("DUTIES","DROITS")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Previous balance","Solde Précédent")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Cash fx","Cash FX")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("PAYROLL INCOME","REVENU DE PAIE")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("TELEPHONE CHARGES","Frais de Téléphone")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Clearing","Compensation")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Hotel","Hôtel")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Miscellaneous","Divers")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Corporate Card-Out-of-Poc","")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Traveling Dolby Empl","Employé itinérant de Dolby")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Tools-Equipment-Lab Supplies","Outils-Equipement-Fournitures de laboratoire")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("rounding","Arrondissement")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Building Supplies-Maintenance","Matériaux de construction-Entretien")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Expensed Furniture","Mobilier Dépensé")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Credit for Charges","Crédit pour frais")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Manual P-ment and double payment to be deduct","P-mnt manuel et double paiement à déduire")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Employee insurance travel","Assurance de voyage des employés 2019")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Rent ","Location ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Lunch vouchers ","Bons déjeuner")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Store Room ","Chambre Stocke")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Evaluation ","Évaluation  ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Charges ","Frais ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("On Line ","En ligne ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("/Building Supplies/Maintenance","/ Matériaux de construction / Entretien")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Music Instruments","Instruments Musicales")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Employee Awards Recognition", "Récompenses des employés, Reconnaissance")


    gl['EcritureLib'] = gl["EcritureLib"].str.replace("/Daily Allowance","/Indemnité journalière")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("RECLASS ", "RECLASSIFICATION ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Purchase Accounting", "Comptabilité d'achat")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("EXPAT ", " Expatrié ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("FROM ", "DE ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("INVOICE", "FACTURE")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("CLEANUP", "APUREMENT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Repayment", "Restitution")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Office Furniture", "Meubles de bureau")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("anti-stress treatments", "traitements anti-stress")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("UK Tax Return", "Décl. d'impôt Royaume-Uni")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Office Location", "Location de bureau")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Deliver Service", "Service de livraison")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Foreign Office Support", "Soutien aux bureaux étrangères")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Showroom", "Salle d'exposition")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("aditional Services", "Services supplémentaires ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Cofee consumption Paris office", "Consommation de café Bureau de Paris")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Consultant ", "Expert-conseil")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("INVOICE", "FACTURE")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Rent-", "Location-")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Corporate", "Entreprise")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("COST ", "COÛT ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("TRAINING", "Formation")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("LIFE DISAB", "Invalidité")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("INSU ", "ASSURANCE ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("PATENT AWARD", "BREVET")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("EQUIVALENT POUR UNUSED VACATION POUR LEAVE", "CONGÉ DE VACANCES INUTILISÉS")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("SPOT ", "")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("AIRFARE TRANSFER TO PREPAIDS", "TRANSFERT DE TRANSPORT AÉRIEN À PAYÉ D'AVANCE")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("WITHHOLDING", "RETRAIT")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Clear ", "Reglement ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Clear ", "Reglement ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Rent/", "Location/")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Pay ", "Paiement ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("PAYMENT", "Paiement ")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("French Income Tax Return;", "Déclaration de revenus française;")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("REVESERVICES", "SERVICES")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("INCLUDED DOUBLE", "DOUBLE INCLUS")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Bank", "Banque")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("/Promotional Expenses", "/Frais de promotion")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace(" ACTIVITY ", " activité ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace(" DEFINED BENEFIT LIABILITY", "PASSIF À AVANTAGES DÉTERMINÉES")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("COÛT PLUS ", "Revient Majoré")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Airline Frais", "Tarifs aériens")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Tools Equipment Lab Supplies", "Outils, Équipement, Fournitures de laboratoire")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace(" Rent", " Location")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Payment Posting", "Paiements")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("COMMISSION D’ACCUMULATION", "ACCUMULATIONS DE COMISSIONS")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("ImpôtE", "Impôt")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("MED.INSU", "MED.ASSURANCE")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("APPRENTICESHIP_CONTRIBUTIONS_TRUE_UP", "CONTRIBUTIONS À L'APPRENTISSAGE/TRUE UP")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("NET PAY", "SALAIRE NET")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("CASH ", "ARGENT ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Repayment ", "Repaiement ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Acct. ", "Comptab. ")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("ACCR ", "ACC ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Accr ", "Acc.")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Cash Balance", "Solde de caisse")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("RECLASS ", "RECLASSEMENT ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("VAT FILING ", "Dépôt de TVA ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Needs to be re-booked due", "KI")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("reclass from", "reclasser de")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("RECLASS FROM", "reclasser de")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("PAYROLL", "PAIE")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("RECLASS ", "Reclasser")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("DEDICTION","DEDUCTION")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Cash","Argent ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("cash ","argent ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("ReclasserIFICATIO","RECLASSEMENT ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("ImpôtS ","Impôts ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Working Repas (Employees Only) ","Repas de travail (employés seulement) ")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("/Banque Frais","/Frais Bancaires")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("MED. INS.","ASSURANCE MED.")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("Facture - Brut'","Facture - Brute'")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace("_20181130_ MK063850","FACTURE COUPA")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("_20181130_ MS063849","FACTURE COUPA")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("_20181130_ MB063846","FACTURE COUPA")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("_20181231_ MK063850","FACTURE COUPA")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("_20181231_ MK063850","FACTURE COUPA")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("_20190228_ MK063850","FACTURE COUPA")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("_20190331_ MB063846","FACTURE COUPA")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("_20190430_ MS063849","FACTURE COUPA")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("_20190430_ MB063846","FACTURE COUPA")




    gl['EcritureLib'] = gl['EcritureLib'].str.replace('-', '')
    
    gl['EcritureLib'] = gl['EcritureLib'].str.replace('Contre Passation', 'CP')

    mapping_Valuation1 = {" Valuation on": " Évaluation"," Valuation on Reverse":" Évaluation Contre Passation",
                         " Reverse Posting":" Contre-Passation d'Ecriture -  Conversion de devise ",
                         " Translation Using":" Conversion de devise"}
    mapping_AA1 = {"Reclass from": " Reclassification de", "reclass from": " Reclassification de", "ZEE MEDIA":"ZEE MEDIA Campaignes Numériques", "TRAINING CONTRI. ER JANUARY '19":"FORMATION CONTRI. ER JANVIER' 19",
                  "TAX FEES":"Taxes","SOCIAL SECURITY: URSSAF":"SÉCURITÉ SOCIALE: URSSAF","SOCIAL SECURITY: TRAINING CONTRIBUTIONS":"SÉCURITÉ SOCIALE: CONTRIBUTIONS À LA FORMATION",
                  "SOCIAL SECURITY: APPRENTICESHIP CONTRIBU":"SÉCURITÉ SOCIALE: CONTRIBUTION À L’APPRENTISSAGE","RSM":"SERVICES DE PAIE RSM EF18","RSA":"SERVICES DE PAIE RSA OCT-JAN",
                  "PRIVATE HEALTH":"SANTÉ PRIVÉE: ASSURANCE MÉDICALE-AXA/","PENSION: PENSION CONTRIBUTIONS - REUNICA":"PENSION: COTISATIONS DE RETRAITE-REUNICA","PENSION: LIFE & DISABILITY INSURANCE - R":"PENSION: ASSURANCE VIE & INVALIDITÉ-R", 
                  "PENSION JANUARY '19":"PENSION JANVIER '19",
                  "ON CALL JANUARY '19":"Disponible Janvier'19",
                  "NRE + PROJECT INITIATION FEES":"NRE + FRAIS D’INITIATION AU PROJET (PO 750003","NET PAY JANUARY '19":"Payeante Janvier'19","JANUARY'19":"JANVIER'19",
                  "LUNCH VOUCHER- WITHHOLDING":"BON DÉJEUNER-RETENUE","HOLIDAY BONUS ACCRUAL FY18/19":"CUMUL DES PRIMES DE VACANCES EF18/19",
                  "GROSS SALARY JANUARY '19":"SALAIRE BRUT JANVIER' 19","EMEA ACCRUAL P8FY19":"P8FY19 D’ACCUMULATION EMEA","COMMISSION RE-ACCRUAL":"COMMISSION RÉ-ACCUMULATION",
                  "COMMISSION ACCRUAL":"COMMISSION D’ACCUMULATION","MARCH":"MARS","MAY":"MAI","APRIL":"AVRIL","AUDIT FEES":"HONORAIRES D’AUDIT",
                  "UNSUBMITTED_UNPOSTED BOA ACCRUAL":"Accumulation BOA non soumise non exposée","UNASSIGNED CREDITCARD BOA ACCRUAL":"NON ASSIGNÉ CREDITCARD BOA ACCUMULATION ",
                  "EMEA ACCRUAL":"ACCUMULATION EMEA","Exhibit Expenses":"Frais d'exposition","Hotel Tax":"Taxe hôtelière","Company Events":"Événements d'entreprise",
                  "Public Transport":"Transport public", "Agency Booking Fees":"Frais de réservation d'agence","Working Meals (Employees Only)":"Repas de travail (employés seulement)",
                  "Airfare":"Billet d'avion","Office Supplies":"Fournitures de bureau","Tolls":"Péages",
                  "write off difference see e-mail attached":"radiation de la différence voir e-mail ci-joint",
                 "Manual P/ment and double payment to be deduct":"P/ment manuel et double paiement à déduire","FX DIFFERENCE ON RSU":"DIFFERENCE FX SUR RSU",
                 "DEFINED BENEFIT LIABILITY-TRUE UP":"RESPONSABILITÉ À PRESTATIONS DÉTERMINÉES-TRUE UP","EXTRA RELEASE FOR STORAGE REVERSED":"EXTRA LIBERATION POUR STOCKAGE CONTREPASSATION",
                 "RECLASS BANK CHARGES TO CORRECT COST CEN":"RECLASSER LES FRAIS BANCAIRES POUR CORRIGER","PAYROLL INCOME TAXES":"IMPÔTS SUR LES SALAIRES",
                  "TRAINING TAX TRUE UP":"TAXE DE FORMATION", "FX DIFFERENCE ON STOCK OPTION EXERCISES":"FX DIFFERENCE SUR LES EXERCICES D'OPTIONS STOCK",
                  "Airline Frais":"Frais de Transport Aérien","Agency Booking Fees":"Frais de Réservation d'Agence","Computer Supplies":"Fournitures informatiques",
                 "AUDIT FEES":"FRAIS D'AUDIT", "HOLIDAY BONUS ACCRUAL ":"ACCUMULATION DE BONUS DE VACANCES","TAX FEES":"FRAIS D'IMPÔT",
                  "SOCIAL SECURITY: APPRENTICESHIP CONTRIBU":"SÉCURITÉ SOCIALE: CONTRIBUITION À L’APPRENTISSAGE",
                  "SOCIAL SECURITY: TRAINING CONTRIBUTIONS":"SÉCURITÉ SOCIALE: CONTRIBUTIONS À LA FORMATION", "TRAVEL COST":"FRAIS DE VOYAGE", "HOUSING TAX":"TAXE SUR LE LOGEMENT", 
                 "PAYROLL INCOME TAXES":"IMPÔTS SUR LE REVENU DE LA PAIE","INCOME TAX-PAS":"IMPÔT SUR LE REVENU-PAS", "IC SETTLEMENT":"Règlement Interentreprises",
                 "VACATION TAKEN":"VACANCES PRISES", "SOCIAL SECURITY: APPR. CONTR.":"SÉCURITÉ SOCIALE: CONTRIBUTION À L’APPRENTISSAGE", 
                  "POST OF AVRIL DEC IN CORRECT SIGN":"CORRECTION D'ECRITURE AVRIL DEC"}



    gl = gl.replace({"JournalLib":mapping_Valuation1}, regex=True)
    gl = gl.replace({"JournalLib":mapping_AA1}, regex=True)
    gl['JournalLib'] = gl["JournalLib"].str.replace('COST-PLUS', 'Revient Majoré')
    gl['JournalLib'] = gl["JournalLib"].str.replace('PRITVAE HEALTH: MEDICAL INSURANCE', 'SANTÉ PRIVÉE: ASSURANCE MÉDICALE')
    gl['JournalLib'] = gl["JournalLib"].str.replace('MEDICAL INSURANCE', 'ASSURANCE MÉDICALE')
    gl['JournalLib'] = gl["JournalLib"].str.replace('UNASSIGNED', 'NON ATTRIBUÉ')
    gl['JournalLib'] = gl["JournalLib"].str.replace('Payout', 'Paiement')
    gl['JournalLib'] = gl["JournalLib"].str.replace('FRINGE COST', 'COÛT MARGINAL')
    gl['JournalLib'] = gl["JournalLib"].str.replace('PROJECT INITIATION', 'LANCEMENT DU PROJET')
    gl['JournalLib'] = gl["JournalLib"].str.replace('ACCRUAL', 'ACCUMULATION')
    gl['JournalLib'] = gl["JournalLib"].str.replace('CREDITCARD', 'CARTE DE CRÉDIT')
    gl['JournalLib'] = gl["JournalLib"].str.replace('ACCR ', 'ACCUM ')
    gl['JournalLib'] = gl["JournalLib"].str.replace('VAT ', 'TVA ')
    gl['JournalLib'] = gl["JournalLib"].str.replace('SOCIAL SECURITY ', 'SÉCURITÉ SOCIALE')
    gl['JournalLib'] = gl["JournalLib"].str.replace('SEPTEMBER', 'SEPT')
    gl['JournalLib'] = gl["JournalLib"].str.replace('TAXBACK', 'Reboursement')
    gl['JournalLib'] = gl["JournalLib"].str.replace('REPORT', '')
    gl['JournalLib'] = gl["JournalLib"].str.replace("Reverse Posting", "Contre Passation d'Ecriture")
    gl['JournalLib'] = gl["JournalLib"].str.replace("BASE RENT", "Location Base")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Rent ", "Location ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("RENT ", "Location ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("CLEARING", "compensation ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("clearing", "compensation ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("BILLING CHARGES", "FRAIS DE FACTURATION ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("UNPAID", "NON PAYÉ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("PROPERTY TAX", "IMPÔT FONCIER ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Trans. Using", "Conversion sur")
    gl['JournalLib'] = gl["JournalLib"].str.replace("SALARIES", "Salaires")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Refund", "Remboursement")
    gl['JournalLib'] = gl["JournalLib"].str.replace("REFUND", "Remboursement")
    gl['JournalLib'] = gl["JournalLib"].str.replace("no invoice", "pas de facture")
    gl['JournalLib'] = gl["JournalLib"].str.replace("COST-PLUS SERVICE REVENUE", "Revenus de service Revient Majoré")
    gl['JournalLib'] = gl["JournalLib"].str.replace("SETTLEMENT", "RÈGLEMENT ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("PURCHASE", "ACHAT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("NON-CP SETTLE", "RÈGLEMENT NON-CP")
    gl['JournalLib'] = gl["JournalLib"].str.replace("PAID ", " Payé ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("FEES ", "Frais")

    gl['JournalLib'] = gl["JournalLib"].str.replace("January", "Janvier")
    gl['JournalLib'] = gl["JournalLib"].str.replace("February", "Février")
    gl['JournalLib'] = gl["JournalLib"].str.replace("March", "Mars")
    gl['JournalLib'] = gl["JournalLib"].str.replace("April", "Avril")
    gl['JournalLib'] = gl["JournalLib"].str.replace("May", "Mai")
    gl['JournalLib'] = gl["JournalLib"].str.replace("June", "Juin")
    gl['JournalLib'] = gl["JournalLib"].str.replace("July", "Juillet")
    gl['JournalLib'] = gl["JournalLib"].str.replace("September", "Septembre")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Aug.", "Août")

    gl['JournalLib'] = gl["JournalLib"].str.replace("JANUARY", "Janvier")
    gl['JournalLib'] = gl["JournalLib"].str.replace("FEBRUARY", "Février")
    gl['JournalLib'] = gl["JournalLib"].str.replace("MARCH", "Mars")
    gl['JournalLib'] = gl["JournalLib"].str.replace("APRIL", "Avril")
    gl['JournalLib'] = gl["JournalLib"].str.replace("MAY", "Mai")
    gl['JournalLib'] = gl["JournalLib"].str.replace("JUNE", "Juin")
    gl['JournalLib'] = gl["JournalLib"].str.replace("JULY", "Juillet")
    gl['JournalLib'] = gl["JournalLib"].str.replace("SEPTEMBER", "Septembre")
    gl['JournalLib'] = gl["JournalLib"].str.replace("AUGUST.", "Août")
    gl['JournalLib'] = gl["JournalLib"].str.replace("NOVEMBER.", "Novembre")
    gl['JournalLib'] = gl["JournalLib"].str.replace("DECEMBER.", "Décembre")
    gl['JournalLib'] = gl["JournalLib"].str.replace("December", "Décembre")

    gl['JournalLib'] = gl["JournalLib"].str.replace("Feb.", "Fév.")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Mar.", "Mars")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Apr.", "Avril")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Aug.", "Août")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Aug.", "Août")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Reverse ", "Contre-passation ")

    gl['JournalLib'] = gl["JournalLib"].str.replace("INTEREST CHARGE", "CHARGE D'INTÉRÊT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("-SICK LEAVE PAY", "-Paiement congé maladie")
    gl['JournalLib'] = gl["JournalLib"].str.replace("RECLASSEMENTIFICATION", "RECLASSIFICATION")
    gl['JournalLib'] = gl["JournalLib"].str.replace("INSTALMENT", "VERSEMENT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("FIRST", "1ere")
    gl['JournalLib'] = gl["JournalLib"].str.replace("FINE LATE PAY.", "Amende pour retard de paiement")
    gl['JournalLib'] = gl["JournalLib"].str.replace("-PATERNITY PAY", "Indemnités de paternité")
    gl['JournalLib'] = gl["JournalLib"].str.replace("SOCIAL SECURITY:", "SÉCURITÉ SOCIALE:")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Trip from", "Voyage de:")
    gl['JournalLib'] = gl["JournalLib"].str.replace(" To ", " à")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Shipping", "Livraison")
    gl['JournalLib'] = gl["JournalLib"].str.replace("VOXEET INTEGRATION COSTS", "COÛTS D'INTÉGRATION DE VOXEET")
    gl['JournalLib'] = gl["JournalLib"].str.replace("INCOME TAX", "IMPÔT SUR LE REVENU")
    gl['JournalLib'] = gl["JournalLib"].str.replace('Rideshare', 'Covoiturage')
    gl['JournalLib'] = gl["JournalLib"].str.replace('Travel Meals', 'Repas de Travail')
    gl['JournalLib'] = gl["JournalLib"].str.replace('Fees', 'Frais')
    gl['JournalLib'] = gl["JournalLib"].str.replace('Phone', 'Téléphone')
    gl['JournalLib'] = gl["JournalLib"].str.replace("Books", "Abonnements")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Subcriptions", "Location Base")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Meals", "Repas")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Entertainment", "divertissement ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Third Party", "tiers ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Training Fees", "Frais d0 Formation")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Conferences/Tradeshows Registratio", "Conférences/Tradeshows Enregistrement")
    gl['JournalLib'] = gl["JournalLib"].str.replace("FOR", "POUR")
    gl['JournalLib'] = gl["JournalLib"].str.replace("ROUNDING", "ARRONDISSEMENT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("STORAGE", "STOCKAGE")
    gl['JournalLib'] = gl["JournalLib"].str.replace("VACATION ACCURAL", "Vacances Accumulées")
    gl['JournalLib'] = gl["JournalLib"].str.replace("RECEIVABLE ", "Recevables")
    gl['JournalLib'] = gl["JournalLib"].str.replace("AFTER PAYOUT ", "APRÈS PAIEMENT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("CLEAN UP ", "APUREMENT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("EMPLOYEE TRAVEL INSUR ", "ASSURANCE DE VOYAGE DES EMPLOYÉS")
    gl['JournalLib'] = gl["JournalLib"].str.replace("CORRECTION OF", "CORRECTION DE")
    gl['JournalLib'] = gl["JournalLib"].str.replace("TAXES PAYROLL", "IMPÔTS SUR LA MASSE SALARIALE")
    gl['JournalLib'] = gl["JournalLib"].str.replace("ACCOUNT", "COMPTE")
    gl['JournalLib'] = gl["JournalLib"].str.replace("TAX", "Impôt")
    gl['JournalLib'] = gl["JournalLib"].str.replace("life disab", "Incapacité de vie")
    gl['JournalLib'] = gl["JournalLib"].str.replace("HOUSING TAX","TAXE D'HABITATION")
    gl['JournalLib'] = gl["JournalLib"].str.replace("GROSS SALARY","SALAIRE BRUT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Cleaning Services","Nettoyage")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Freight","Fret")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Membership","adhésion")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Air cooling Maintenance","Entretien de refroidissement de l'air")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Power on Demand Platform","Plateforme d'energie à la demande")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Sanitaire room installation"," Installation de la salle sanitaire")
    gl['JournalLib'] = gl["JournalLib"].str.replace("subscription","abonnement")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Coffee supplies "," Fournitures de café")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Duty and Tax ","Devoir et fiscalité")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Electricity ","Electricité ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Lunch vouchers  ","Bons déjeuner")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Security monitoring","Surveillance de la sécurité")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Water", "L'EAU")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Statutory Audit", "Audit statutaire")
    gl['JournalLib'] = gl["JournalLib"].str.replace(" Meeting room screen installation", "Installation de l'écran de la salle de réunion")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Water", "L'EAU")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Water", "L'EAU")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Tax Credit FY 2016", "Crédit d'impôt Exercice 2016")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Bank of America Merill Lynch-T&E statement","Déclaration de Merill Lynch")
    gl['JournalLib'] = gl["JournalLib"].str.replace("English Translation", "Traduction anglaise")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Office Rent", "Location de Bureau")

    gl['JournalLib'] = gl["JournalLib"].str.replace("Annual Electrical Verification", "Vérification électrique annuelle ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Health costs ", "Coûts santé")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Unlimited-receipt and policy audit", "Vérification illimitée des reçus et audites")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Water fountain ", "Fontaine d'eau")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Quartely control visit", "Visite de contrôle trimestrielle")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Fire extinguishers annual check", "Vérification annuelle des extincteurs")
    gl['JournalLib'] = gl["JournalLib"].str.replace("showroom rent", "location de salle d'exposition")
    gl['JournalLib'] = gl["JournalLib"].str.replace("AND ACTUAL RECEIV","ET RECETTES RÉELLES")
    gl['JournalLib'] = gl["JournalLib"].str.replace("FILING","DÉPÔT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("ORDERS","ORDRES")
    gl['JournalLib'] = gl["JournalLib"].str.replace("EXCLUDED -DUMMY CREDIT","EXCLU")
    gl['JournalLib'] = gl["JournalLib"].str.replace("RELARING TO","RELATIF À")
    gl['JournalLib'] = gl["JournalLib"].str.replace("CLEAN UP-","APUREMENT-")
    gl['JournalLib'] = gl["JournalLib"].str.replace("2ND INSTALLEMENT","2ème versement")
    gl['JournalLib'] = gl["JournalLib"].str.replace("DOUBLE PAYMENT","DOUBLE PAIEMENT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("CLEAN UP-","APUREMENT-")
    gl['JournalLib'] = gl["JournalLib"].str.replace("DUTIES","DROITS")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Previous balance","Solde Précédent")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Cash fx","Cash FX")
    gl['JournalLib'] = gl["JournalLib"].str.replace("PAYROLL INCOME","REVENU DE PAIE")
    gl['JournalLib'] = gl["JournalLib"].str.replace("TELEPHONE CHARGES","Frais de Téléphone")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Clearing","Compensation")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Hotel","Hôtel")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Miscellaneous","Divers")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Corporate Card-Out-of-Poc","")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Traveling Dolby Empl","Employé itinérant de Dolby")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Tools-Equipment-Lab Supplies","Outils-Equipement-Fournitures de laboratoire")
    gl['JournalLib'] = gl["JournalLib"].str.replace("rounding","Arrondissement")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Building Supplies-Maintenance","Matériaux de construction-Entretien")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Expensed Furniture","Mobilier Dépensé")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Credit for Charges","Crédit pour frais")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Manual P-ment and double payment to be deduct","P-mnt manuel et double paiement à déduire")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Employee insurance travel","Assurance de voyage des employés 2019")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Rent ","Location ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Lunch vouchers ","Bons déjeuner")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Store Room ","Chambre Stocke")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Evaluation ","Évaluation  ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Charges ","Frais ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("On Line ","En ligne ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("/Building Supplies/Maintenance","/ Matériaux de construction / Entretien")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Music Instruments","Instruments Musicales")
    gl['JournalLib'] = gl["JournalLib"].str.replace("/Employee Awards/Recognition", "/ Récompenses des employés / Reconnaissance")


    gl['JournalLib'] = gl["JournalLib"].str.replace("/Daily Allowance","/Indemnité journalière")

    gl['JournalLib'] = gl["JournalLib"].str.replace("RECLASS ", "RECLASSIFICATION ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Purchase Accounting", "Comptabilité d'achat")
    gl['JournalLib'] = gl["JournalLib"].str.replace( "EXPAT ", " Expatrié ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("FROM ", "DE ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("INVOICE", "FACTURE")
    gl['JournalLib'] = gl["JournalLib"].str.replace("CLEANUP", "APUREMENT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Repayment", "Restitution")

    gl['JournalLib'] = gl["JournalLib"].str.replace("Office Furniture", "Meubles de bureau")
    gl['JournalLib'] = gl["JournalLib"].str.replace("anti-stress treatments", "traitements anti-stress")

    gl['JournalLib'] = gl["JournalLib"].str.replace("UK Tax Return", "Décl. d'impôt Royaume-Uni")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Office Location", "Location de bureau")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Deliver Service", "Service de livraison")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Foreign Office Support", "Soutien aux bureaux étrangères")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Showroom", "Salle d'exposition")

    gl['JournalLib'] = gl["JournalLib"].str.replace("aditional Services", "Services supplémentaires ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Cofee consumption Paris office", "Consommation de café Bureau de Paris")

    gl['JournalLib'] = gl["JournalLib"].str.replace("Consultant ", "Expert-conseil")
    gl['JournalLib'] = gl["JournalLib"].str.replace("INVOICE", "FACTURE")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Rent-", "Location-")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Corporate", "Entreprise")
    gl['JournalLib'] = gl["JournalLib"].str.replace("COST ", "COÛT ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("TRAINING", "Formation")
    gl['JournalLib'] = gl["JournalLib"].str.replace("LIFE DISAB", "Invalidité")
    gl['JournalLib'] = gl["JournalLib"].str.replace("INSU ", "ASSURANCE ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("PATENT AWARD", "BREVET")

    gl['JournalLib'] = gl["JournalLib"].str.replace("EQUIVALENT POUR UNUSED VACATION POUR LEAVE", "CONGÉ DE VACANCES INUTILISÉS")
    gl['JournalLib'] = gl["JournalLib"].str.replace("SPOT ", "")
    gl['JournalLib'] = gl["JournalLib"].str.replace("AIRFARE TRANSFER TO PREPAIDS", "TRANSFERT DE TRANSPORT AÉRIEN À PAYÉ D'AVANCE")
    gl['JournalLib'] = gl["JournalLib"].str.replace("WITHHOLDING", "RETRAIT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Clear ", "Reglement ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Clear ", "Reglement ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Rent/", "Location/")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Pay ", "Paiement ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("PAYMENT", "Paiement ")

    gl['JournalLib'] = gl["JournalLib"].str.replace("French Income Tax Return;", "Déclaration de revenus française;")
    gl['JournalLib'] = gl["JournalLib"].str.replace("REVESERVICES", "SERVICES")
    gl['JournalLib'] = gl["JournalLib"].str.replace("INCLUDED DOUBLE", "DOUBLE INCLUS")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Bank", "Banque")
    gl['JournalLib'] = gl["JournalLib"].str.replace("/Promotional Expenses", "/Frais de promotion")

    gl['JournalLib'] = gl["JournalLib"].str.replace(" ACTIVITY ", " activité ")
    gl['JournalLib'] = gl["JournalLib"].str.replace(" DEFINED BENEFIT LIABILITY", "PASSIF À AVANTAGES DÉTERMINÉES")
    gl['JournalLib'] = gl["JournalLib"].str.replace("COÛT PLUS ", "Revient Majoré")
    gl['JournalLib'] = gl["JournalLib"].str.replace("/Airline Frais", "/Tarifs aériens")
    gl['JournalLib'] = gl["JournalLib"].str.replace("/Tools/Equipment/Lab Supplies", "/Outils / Équipement / Fournitures de laboratoire")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Rent/", "Location/")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Payment Posting", "Paiements")
    gl['JournalLib'] = gl["JournalLib"].str.replace("COMMISSION D’ACCUMULATION", "ACCUMULATIONS DE COMISSIONS")
    gl['JournalLib'] = gl["JournalLib"].str.replace("ImpôtE", "Impôt")
    gl['JournalLib'] = gl["JournalLib"].str.replace("MED.INSU", "MED.ASSURANCE")
    gl['JournalLib'] = gl["JournalLib"].str.replace("APPRENTICESHIP_CONTRIBUTIONS_TRUE_UP", "CONTRIBUTIONS À L'APPRENTISSAGE/TRUE UP")
    gl['JournalLib'] = gl["JournalLib"].str.replace("NET PAY", "SALAIRE NET")
    gl['JournalLib'] = gl["JournalLib"].str.replace("CASH ", "ARGENT ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Repayment ", "Repaiement ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Acct. ", "Comptab. ")

    gl['JournalLib'] = gl["JournalLib"].str.replace("ACCR ", "ACC ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Accr ", "Acc.")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Cash Balance", "Solde de caisse")
    gl['JournalLib'] = gl["JournalLib"].str.replace("RECLASS ", "RECLASSEMENT ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("VAT FILING ", "Dépôt de TVA ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Needs to be re-booked due", "KI")
    gl['JournalLib'] = gl["JournalLib"].str.replace("reclass from", "reclasser de")
    gl['JournalLib'] = gl["JournalLib"].str.replace("RECLASS FROM", "reclasser de")
    gl['JournalLib'] = gl["JournalLib"].str.replace("PAYROLL", "PAIE")
    gl['JournalLib'] = gl["JournalLib"].str.replace("RECLASS ", "Reclasser")

    gl['JournalLib'] = gl["JournalLib"].str.replace("DEDICTION","DEDUCTION")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Cash","Argent ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("cash ","argent ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("ReclasserIFICATIO","RECLASSEMENT ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("ImpôtS ","Impôts ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Working Repas (Employees Only) ","Repas de travail (employés seulement) ")
    gl['JournalLib'] = gl["JournalLib"].str.replace("/Banque Frais","/Frais Bancaires")
    gl['JournalLib'] = gl["JournalLib"].str.replace("MED. INS.","ASSURANCE MED.")
    gl['JournalLib'] = gl["JournalLib"].str.replace("AJE WIRE LOG TRAN","AJE VERSEMENT")
    gl['JournalLib'] = gl["JournalLib"].str.replace("JUN'","JUIN'")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Deferred Rent18 rue de Lo","Loyer différé 18 Rue de Lo")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Facture - Brut'","Facture - Brute")
    gl['JournalLib'] = gl["JournalLib"].str.replace("T&E","VD")
    gl['JournalLib'] = gl["JournalLib"].str.replace("Inv","Facture")
    gl['JournalLib'] = gl["JournalLib"].str.replace("2019`","2019")
    gl['JournalLib'] = gl["JournalLib"].str.replace("-2014V","")

    
    mapping_Valuation1 = {" Valuation on": " Évaluation"," Valuation on Reverse":" Évaluation Contre Passation",
                         " Reverse Posting":" Contre-Passation d'Ecriture -  Conversion de devise",
                         " Translation Using":" Conversion de devise"}
    mapping_AA1 = {"Reclass from": " Reclassification de", "reclass from": " Reclassification de", "ZEE MEDIA":"ZEE MEDIA Campaignes Numériques", "TRAINING CONTRI. ER JANUARY '19":"FORMATION CONTRI. ER JANVIER' 19",
                  "TAX FEES":"Taxes","SOCIAL SECURITY: URSSAF":"SÉCURITÉ SOCIALE: URSSAF","SOCIAL SECURITY: TRAINING CONTRIBUTIONS":"SÉCURITÉ SOCIALE: CONTRIBUTIONS À LA FORMATION",
                  "SOCIAL SECURITY: APPRENTICESHIP CONTRIBU":"SÉCURITÉ SOCIALE: CONTRIBUTION À L’APPRENTISSAGE","RSM":"SERVICES DE PAIE RSM EF18","RSA":"SERVICES DE PAIE RSA OCT-JAN",
                  "PRIVATE HEALTH":"SANTÉ PRIVÉE: ASSURANCE MÉDICALE-AXA/","PENSION: PENSION CONTRIBUTIONS - REUNICA":"PENSION: COTISATIONS DE RETRAITE-REUNICA","PENSION: LIFE & DISABILITY INSURANCE - R":"PENSION: ASSURANCE VIE & INVALIDITÉ-R", 
                  "PENSION JANUARY '19":"PENSION JANVIER '19",
                  "ON CALL JANUARY '19":"Disponible Janvier'19",
                  "NRE + PROJECT INITIATION FEES":"NRE + FRAIS D’INITIATION AU PROJET (PO 750003","NET PAY JANUARY '19":"Payeante Janvier'19","JANUARY'19":"JANVIER'19",
                  "LUNCH VOUCHER- WITHHOLDING":"BON DÉJEUNER-RETENUE","HOLIDAY BONUS ACCRUAL FY18/19":"CUMUL DES PRIMES DE VACANCES EF18/19",
                  "GROSS SALARY JANUARY '19":"SALAIRE BRUT JANVIER' 19","EMEA ACCRUAL P8FY19":"P8FY19 D’ACCUMULATION EMEA","COMMISSION RE-ACCRUAL":"COMMISSION RÉ-ACCUMULATION",
                  "COMMISSION ACCRUAL":"COMMISSION D’ACCUMULATION","MARCH":"MARS","MAY":"MAI","APRIL":"AVRIL","AUDIT FEES":"HONORAIRES D’AUDIT",
                  "UNSUBMITTED_UNPOSTED BOA ACCRUAL":"Accumulation BOA non soumise non exposée","UNASSIGNED CREDITCARD BOA ACCRUAL":"NON ASSIGNÉ CREDITCARD BOA ACCUMULATION ",
                  "EMEA ACCRUAL":"ACCUMULATION EMEA","Exhibit Expenses":"Frais d'exposition","Hotel Tax":"Taxe hôtelière","Company Events":"Événements d'entreprise",
                  "Public Transport":"Transport public", "Agency Booking Fees":"Frais de réservation d'agence","Working Meals (Employees Only)":"Repas de travail (employés seulement)",
                  "Airfare":"Billet d'avion","Office Supplies":"Fournitures de bureau","Tolls":"Péages",
                  "write off difference see e-mail attached":"radiation de la différence voir e-mail ci-joint",
                 "Manual P/ment and double payment to be deduct":"P/ment manuel et double paiement à déduire","FX DIFFERENCE ON RSU":"DIFFERENCE FX SUR RSU",
                 "DEFINED BENEFIT LIABILITY-TRUE UP":"RESPONSABILITÉ À PRESTATIONS DÉTERMINÉES-TRUE UP","EXTRA RELEASE FOR STORAGE REVERSED":"EXTRA LIBERATION POUR STOCKAGE CONTREPASSATION",
                 "RECLASS BANK CHARGES TO CORRECT COST CEN":"RECLASSER LES FRAIS BANCAIRES POUR CORRIGER","PAYROLL INCOME TAXES":"IMPÔTS SUR LES SALAIRES",
                  "TRAINING TAX TRUE UP":"TAXE DE FORMATION", "FX DIFFERENCE ON STOCK OPTION EXERCISES":"FX DIFFERENCE SUR LES EXERCICES D'OPTIONS STOCK",
                  "Airline Frais":"Frais de Transport Aérien","Agency Booking Fees":"Frais de Réservation d'Agence","Computer Supplies":"Fournitures informatiques",
                 "AUDIT FEES":"FRAIS D'AUDIT", "HOLIDAY BONUS ACCRUAL ":"ACCUMULATION DE BONUS DE VACANCES","TAX FEES":"FRAIS D'IMPÔT",
                  "SOCIAL SECURITY: APPRENTICESHIP CONTRIBU":"SÉCURITÉ SOCIALE: CONTRIBUITION À L’APPRENTISSAGE",
                  "SOCIAL SECURITY: TRAINING CONTRIBUTIONS":"SÉCURITÉ SOCIALE: CONTRIBUTIONS À LA FORMATION", "TRAVEL COST":"FRAIS DE VOYAGE", "HOUSING TAX":"TAXE SUR LE LOGEMENT", 
                 "PAYROLL INCOME TAXES":"IMPÔTS SUR LE REVENU DE LA PAIE","INCOME TAX-PAS":"IMPÔT SUR LE REVENU-PAS", "IC SETTLEMENT":"Règlement Interentreprises",
                 "VACATION TAKEN":"VACANCES PRISES", "SOCIAL SECURITY: APPR. CONTR.":"SÉCURITÉ SOCIALE: CONTRIBUTION À L’APPRENTISSAGE", 
                  "POST OF AVRIL DEC IN CORRECT SIGN":"CORRECTION D'ECRITURE AVRIL DEC"}



    gl = gl.replace({"PieceRef":mapping_Valuation1}, regex=True)
    gl = gl.replace({"PieceRef":mapping_AA1}, regex=True)
    gl['PieceRef'] = gl["PieceRef"].str.replace('COST-PLUS', 'Revient Majoré')
    gl['PieceRef'] = gl["PieceRef"].str.replace('PRITVAE HEALTH: MEDICAL INSURANCE', 'SANTÉ PRIVÉE: ASSURANCE MÉDICALE')
    gl['PieceRef'] = gl["PieceRef"].str.replace('MEDICAL INSURANCE', 'ASSURANCE MÉDICALE')
    gl['PieceRef'] = gl["PieceRef"].str.replace('UNASSIGNED', 'NON ATTRIBUÉ')
    gl['PieceRef'] = gl["PieceRef"].str.replace('Payout', 'Paiement')
    gl['PieceRef'] = gl["PieceRef"].str.replace('FRINGE COST', 'COÛT MARGINAL')
    gl['PieceRef'] = gl["PieceRef"].str.replace('PROJECT INITIATION', 'LANCEMENT DU PROJET')
    gl['PieceRef'] = gl["PieceRef"].str.replace('ACCRUAL', 'ACCUMULATION')
    gl['PieceRef'] = gl["PieceRef"].str.replace('CREDITCARD', 'CARTE DE CRÉDIT')
    gl['PieceRef'] = gl["PieceRef"].str.replace('ACCR ', 'ACCUM ')
    gl['PieceRef'] = gl["PieceRef"].str.replace('VAT ', 'TVA ')
    gl['PieceRef'] = gl["PieceRef"].str.replace('SOCIAL SECURITY ', 'SÉCURITÉ SOCIALE')
    gl['PieceRef'] = gl["PieceRef"].str.replace('SEPTEMBER', 'SEPT')
    gl['PieceRef'] = gl["PieceRef"].str.replace('TAXBACK', 'Reboursement')
    gl['PieceRef'] = gl["PieceRef"].str.replace('REPORT', '')
    gl['PieceRef'] = gl["PieceRef"].str.replace("Reverse Posting", "Contre Passation d'Ecriture")
    gl['PieceRef'] = gl["PieceRef"].str.replace("BASE RENT", "Location Base")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Rent ", "Location ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("RENT ", "Location ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("CLEARING", "compensation ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("clearing", "compensation ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("BILLING CHARGES", "FRAIS DE FACTURATION ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("UNPAID", "NON PAYÉ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("PROPERTY TAX", "IMPÔT FONCIER ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Trans. Using", "Conversion sur")
    gl['PieceRef'] = gl["PieceRef"].str.replace("SALARIES", "Salaires")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Refund", "Remboursement")
    gl['PieceRef'] = gl["PieceRef"].str.replace("REFUND", "Remboursement")
    gl['PieceRef'] = gl["PieceRef"].str.replace("no invoice", "pas de facture")
    gl['PieceRef'] = gl["PieceRef"].str.replace("COST-PLUS SERVICE REVENUE", "Revenus de service Revient Majoré")
    gl['PieceRef'] = gl["PieceRef"].str.replace("SETTLEMENT", "RÈGLEMENT ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("PURCHASE", "ACHAT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("NON-CP SETTLE", "RÈGLEMENT NON-CP")
    gl['PieceRef'] = gl["PieceRef"].str.replace("PAID ", " Payé ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("FEES ", "Frais")

    gl['PieceRef'] = gl["PieceRef"].str.replace("January", "Janvier")
    gl['PieceRef'] = gl["PieceRef"].str.replace("February", "Février")
    gl['PieceRef'] = gl["PieceRef"].str.replace("March", "Mars")
    gl['PieceRef'] = gl["PieceRef"].str.replace("April", "Avril")
    gl['PieceRef'] = gl["PieceRef"].str.replace("May", "Mai")
    gl['PieceRef'] = gl["PieceRef"].str.replace("June", "Juin")
    gl['PieceRef'] = gl["PieceRef"].str.replace("July", "Juillet")
    gl['PieceRef'] = gl["PieceRef"].str.replace("September", "Septembre")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Aug.", "Août")

    gl['PieceRef'] = gl["PieceRef"].str.replace("JANUARY", "Janvier")
    gl['PieceRef'] = gl["PieceRef"].str.replace("FEBRUARY", "Février")
    gl['PieceRef'] = gl["PieceRef"].str.replace("MARCH", "Mars")
    gl['PieceRef'] = gl["PieceRef"].str.replace("APRIL", "Avril")
    gl['PieceRef'] = gl["PieceRef"].str.replace("MAY", "Mai")
    gl['PieceRef'] = gl["PieceRef"].str.replace("JUNE", "Juin")
    gl['PieceRef'] = gl["PieceRef"].str.replace("JULY", "Juillet")
    gl['PieceRef'] = gl["PieceRef"].str.replace("SEPTEMBER", "Septembre")
    gl['PieceRef'] = gl["PieceRef"].str.replace("AUGUST.", "Août")
    gl['PieceRef'] = gl["PieceRef"].str.replace("NOVEMBER.", "Novembre")
    gl['PieceRef'] = gl["PieceRef"].str.replace("DECEMBER.", "Décembre")
    gl['PieceRef'] = gl["PieceRef"].str.replace("December", "Décembre")

    gl['PieceRef'] = gl["PieceRef"].str.replace("Feb.", "Fév.")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Mar.", "Mars")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Apr.", "Avril")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Aug.", "Août")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Aug.", "Août")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Reverse ", "Contre-passation ")

    gl['PieceRef'] = gl["PieceRef"].str.replace("INTEREST CHARGE", "CHARGE D'INTÉRÊT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("-SICK LEAVE PAY", "-Paiement congé maladie")
    gl['PieceRef'] = gl["PieceRef"].str.replace("RECLASSEMENTIFICATION", "RECLASSIFICATION")
    gl['PieceRef'] = gl["PieceRef"].str.replace("INSTALMENT", "VERSEMENT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("FIRST", "1ere")
    gl['PieceRef'] = gl["PieceRef"].str.replace("FINE LATE PAY.", "Amende pour retard de paiement")
    gl['PieceRef'] = gl["PieceRef"].str.replace("-PATERNITY PAY", "Indemnités de paternité")
    gl['PieceRef'] = gl["PieceRef"].str.replace("SOCIAL SECURITY:", "SÉCURITÉ SOCIALE:")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Trip from", "Voyage de:")
    gl['PieceRef'] = gl["PieceRef"].str.replace(" To ", " à")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Shipping", "Livraison")
    gl['PieceRef'] = gl["PieceRef"].str.replace("VOXEET INTEGRATION COSTS", "COÛTS D'INTÉGRATION DE VOXEET")
    gl['PieceRef'] = gl["PieceRef"].str.replace("INCOME TAX", "IMPÔT SUR LE REVENU")
    gl['PieceRef'] = gl["PieceRef"].str.replace('Rideshare', 'Covoiturage')
    gl['PieceRef'] = gl["PieceRef"].str.replace('Travel Meals', 'Repas de Travail')
    gl['PieceRef'] = gl["PieceRef"].str.replace('Fees', 'Frais')
    gl['PieceRef'] = gl["PieceRef"].str.replace('Phone', 'Téléphone')
    gl['PieceRef'] = gl["PieceRef"].str.replace("Books", "Abonnements")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Subcriptions", "Location Base")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Meals", "Repas")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Entertainment", "divertissement ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Third Party", "tiers ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Training Fees", "Frais d0 Formation")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Conferences/Tradeshows Registratio", "Conférences/Tradeshows Enregistrement")
    gl['PieceRef'] = gl["PieceRef"].str.replace("FOR", "POUR")
    gl['PieceRef'] = gl["PieceRef"].str.replace("ROUNDING", "ARRONDISSEMENT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("STORAGE", "STOCKAGE")
    gl['PieceRef'] = gl["PieceRef"].str.replace("VACATION ACCURAL", "Vacances Accumulées")
    gl['PieceRef'] = gl["PieceRef"].str.replace("RECEIVABLE ", "Recevables")
    gl['PieceRef'] = gl["PieceRef"].str.replace("AFTER PAYOUT ", "APRÈS PAIEMENT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("CLEAN UP ", "APUREMENT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("EMPLOYEE TRAVEL INSUR ", "ASSURANCE DE VOYAGE DES EMPLOYÉS")
    gl['PieceRef'] = gl["PieceRef"].str.replace("CORRECTION OF", "CORRECTION DE")
    gl['PieceRef'] = gl["PieceRef"].str.replace("TAXES PAYROLL", "IMPÔTS SUR LA MASSE SALARIALE")
    gl['PieceRef'] = gl["PieceRef"].str.replace("ACCOUNT", "COMPTE")
    gl['PieceRef'] = gl["PieceRef"].str.replace("TAX", "Impôt")
    gl['PieceRef'] = gl["PieceRef"].str.replace("life disab", "Incapacité de vie")
    gl['PieceRef'] = gl["PieceRef"].str.replace("HOUSING TAX","TAXE D'HABITATION")
    gl['PieceRef'] = gl["PieceRef"].str.replace("GROSS SALARY","SALAIRE BRUT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Cleaning Services","Nettoyage")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Freight","Fret")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Membership","adhésion")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Air cooling Maintenance","Entretien de refroidissement de l'air")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Power on Demand Platform","Plateforme d'energie à la demande")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Sanitaire room installation"," Installation de la salle sanitaire")
    gl['PieceRef'] = gl["PieceRef"].str.replace("subscription","abonnement")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Coffee supplies "," Fournitures de café")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Duty and Tax ","Devoir et fiscalité")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Electricity ","Electricité ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Lunch vouchers  ","Bons déjeuner")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Security monitoring","Surveillance de la sécurité")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Water", "L'EAU")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Statutory Audit", "Audit statutaire")
    gl['PieceRef'] = gl["PieceRef"].str.replace(" Meeting room screen installation", "Installation de l'écran de la salle de réunion")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Water", "L'EAU")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Water", "L'EAU")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Tax Credit FY 2016", "Crédit d'impôt Exercice 2016")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Bank of America Merill Lynch-T&E statement","Déclaration de Merill Lynch")
    gl['PieceRef'] = gl["PieceRef"].str.replace("English Translation", "Traduction anglaise")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Office Rent", "Location de Bureau")

    gl['PieceRef'] = gl["PieceRef"].str.replace("Annual Electrical Verification", "Vérification électrique annuelle ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Health costs ", "Coûts santé")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Unlimited-receipt and policy audit", "Vérification illimitée des reçus et audites")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Water fountain ", "Fontaine d'eau")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Quartely control visit", "Visite de contrôle trimestrielle")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Fire extinguishers annual check", "Vérification annuelle des extincteurs")
    gl['PieceRef'] = gl["PieceRef"].str.replace("showroom rent", "location de salle d'exposition")
    gl['PieceRef'] = gl["PieceRef"].str.replace("AND ACTUAL RECEIV","ET RECETTES RÉELLES")
    gl['PieceRef'] = gl["PieceRef"].str.replace("FILING","DÉPÔT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("ORDERS","ORDRES")
    gl['PieceRef'] = gl["PieceRef"].str.replace("EXCLUDED -DUMMY CREDIT","EXCLU")
    gl['PieceRef'] = gl["PieceRef"].str.replace("RELARING TO","RELATIF À")
    gl['PieceRef'] = gl["PieceRef"].str.replace("CLEAN UP-","APUREMENT-")
    gl['PieceRef'] = gl["PieceRef"].str.replace("2ND INSTALLEMENT","2ème versement")
    gl['PieceRef'] = gl["PieceRef"].str.replace("DOUBLE PAYMENT","DOUBLE PAIEMENT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("CLEAN UP-","APUREMENT-")
    gl['PieceRef'] = gl["PieceRef"].str.replace("DUTIES","DROITS")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Previous balance","Solde Précédent")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Cash fx","Cash FX")
    gl['PieceRef'] = gl["PieceRef"].str.replace("PAYROLL INCOME","REVENU DE PAIE")
    gl['PieceRef'] = gl["PieceRef"].str.replace("TELEPHONE CHARGES","Frais de Téléphone")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Clearing","Compensation")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Hotel","Hôtel")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Miscellaneous","Divers")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Corporate Card-Out-of-Poc","")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Traveling Dolby Empl","Employé itinérant de Dolby")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Tools-Equipment-Lab Supplies","Outils-Equipement-Fournitures de laboratoire")
    gl['PieceRef'] = gl["PieceRef"].str.replace("rounding","Arrondissement")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Building Supplies-Maintenance","Matériaux de construction-Entretien")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Expensed Furniture","Mobilier Dépensé")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Credit for Charges","Crédit pour frais")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Manual P-ment and double payment to be deduct","P-mnt manuel et double paiement à déduire")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Employee insurance travel","Assurance de voyage des employés 2019")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Rent ","Location ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Lunch vouchers ","Bons déjeuner")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Store Room ","Chambre Stocke")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Evaluation ","Évaluation  ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Charges ","Frais ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("On Line ","En ligne ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("/Building Supplies/Maintenance","/ Matériaux de construction / Entretien")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Music Instruments","Instruments Musicales")
    gl['PieceRef'] = gl["PieceRef"].str.replace("/Employee Awards/Recognition", "/ Récompenses des employés / Reconnaissance")


    gl['PieceRef'] = gl["PieceRef"].str.replace("/Daily Allowance","/Indemnité journalière")

    gl['PieceRef'] = gl["PieceRef"].str.replace("RECLASS ", "RECLASSIFICATION ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Purchase Accounting", "Comptabilité d'achat")
    gl['PieceRef'] = gl["PieceRef"].str.replace( "EXPAT ", " Expatrié ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("FROM ", "DE ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("INVOICE", "FACTURE")
    gl['PieceRef'] = gl["PieceRef"].str.replace("CLEANUP", "APUREMENT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Repayment", "Restitution")

    gl['PieceRef'] = gl["PieceRef"].str.replace("Office Furniture", "Meubles de bureau")
    gl['PieceRef'] = gl["PieceRef"].str.replace("anti-stress treatments", "traitements anti-stress")

    gl['PieceRef'] = gl["PieceRef"].str.replace("UK Tax Return", "Décl. d'impôt Royaume-Uni")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Office Location", "Location de bureau")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Deliver Service", "Service de livraison")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Foreign Office Support", "Soutien aux bureaux étrangères")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Showroom", "Salle d'exposition")

    gl['PieceRef'] = gl["PieceRef"].str.replace("aditional Services", "Services supplémentaires ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Cofee consumption Paris office", "Consommation de café Bureau de Paris")

    gl['PieceRef'] = gl["PieceRef"].str.replace("Consultant ", "Expert-conseil")
    gl['PieceRef'] = gl["PieceRef"].str.replace("INVOICE", "FACTURE")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Rent-", "Location-")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Corporate", "Entreprise")
    gl['PieceRef'] = gl["PieceRef"].str.replace("COST ", "COÛT ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("TRAINING", "Formation")
    gl['PieceRef'] = gl["PieceRef"].str.replace("LIFE DISAB", "Invalidité")
    gl['PieceRef'] = gl["PieceRef"].str.replace("INSU ", "ASSURANCE ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("PATENT AWARD", "BREVET")

    gl['PieceRef'] = gl["PieceRef"].str.replace("EQUIVALENT POUR UNUSED VACATION POUR LEAVE", "CONGÉ DE VACANCES INUTILISÉS")
    gl['PieceRef'] = gl["PieceRef"].str.replace("SPOT ", "")
    gl['PieceRef'] = gl["PieceRef"].str.replace("AIRFARE TRANSFER TO PREPAIDS", "TRANSFERT DE TRANSPORT AÉRIEN À PAYÉ D'AVANCE")
    gl['PieceRef'] = gl["PieceRef"].str.replace("WITHHOLDING", "RETRAIT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Clear ", "Reglement ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Clear ", "Reglement ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Rent/", "Location/")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Pay ", "Paiement ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("PAYMENT", "Paiement ")

    gl['PieceRef'] = gl["PieceRef"].str.replace("French Income Tax Return;", "Déclaration de revenus française;")
    gl['PieceRef'] = gl["PieceRef"].str.replace("REVESERVICES", "SERVICES")
    gl['PieceRef'] = gl["PieceRef"].str.replace("INCLUDED DOUBLE", "DOUBLE INCLUS")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Bank", "Banque")
    gl['PieceRef'] = gl["PieceRef"].str.replace("/Promotional Expenses", "/Frais de promotion")

    gl['PieceRef'] = gl["PieceRef"].str.replace(" ACTIVITY ", " activité ")
    gl['PieceRef'] = gl["PieceRef"].str.replace(" DEFINED BENEFIT LIABILITY", "PASSIF À AVANTAGES DÉTERMINÉES")
    gl['PieceRef'] = gl["PieceRef"].str.replace("COÛT PLUS ", "Revient Majoré")
    gl['PieceRef'] = gl["PieceRef"].str.replace("/Airline Frais", "/Tarifs aériens")
    gl['PieceRef'] = gl["PieceRef"].str.replace("/Tools/Equipment/Lab Supplies", "/Outils / Équipement / Fournitures de laboratoire")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Rent/", "Location/")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Payment Posting", "Paiements")
    gl['PieceRef'] = gl["PieceRef"].str.replace("COMMISSION D’ACCUMULATION", "ACCUMULATIONS DE COMISSIONS")
    gl['PieceRef'] = gl["PieceRef"].str.replace("ImpôtE", "Impôt")
    gl['PieceRef'] = gl["PieceRef"].str.replace("MED.INSU", "MED.ASSURANCE")
    gl['PieceRef'] = gl["PieceRef"].str.replace("APPRENTICESHIP_CONTRIBUTIONS_TRUE_UP", "CONTRIBUTIONS À L'APPRENTISSAGE/TRUE UP")
    gl['PieceRef'] = gl["PieceRef"].str.replace("NET PAY", "SALAIRE NET")
    gl['PieceRef'] = gl["PieceRef"].str.replace("CASH ", "ARGENT ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Repayment ", "Repaiement ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Acct. ", "Comptab. ")

    gl['PieceRef'] = gl["PieceRef"].str.replace("ACCR ", "ACC ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Accr ", "Acc.")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Cash Balance", "Solde de caisse")
    gl['PieceRef'] = gl["PieceRef"].str.replace("RECLASS ", "RECLASSEMENT ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("VAT FILING ", "Dépôt de TVA ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Needs to be re-booked due", "KI")
    gl['PieceRef'] = gl["PieceRef"].str.replace("reclass from", "reclasser de")
    gl['PieceRef'] = gl["PieceRef"].str.replace("RECLASS FROM", "reclasser de")
    gl['PieceRef'] = gl["PieceRef"].str.replace("PAYROLL", "PAIE")
    gl['PieceRef'] = gl["PieceRef"].str.replace("RECLASS ", "Reclasser")

    gl['PieceRef'] = gl["PieceRef"].str.replace("DEDICTION","DEDUCTION")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Cash","Argent ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("cash ","argent ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("ReclasserIFICATIO","RECLASSEMENT ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("ImpôtS ","Impôts ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Working Repas (Employees Only) ","Repas de travail (employés seulement) ")
    gl['PieceRef'] = gl["PieceRef"].str.replace("/Banque Frais","/Frais Bancaires")
    gl['PieceRef'] = gl["PieceRef"].str.replace("MED. INS.","ASSURANCE MED.")
    gl['PieceRef'] = gl["PieceRef"].str.replace("AJE WIRE LOG TRAN","AJE VERSEMENT")
    gl['PieceRef'] = gl["PieceRef"].str.replace("JUN'","JUIN'")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Deferred Rent18 rue de Lo","Loyer différé 18 Rue de Lo")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Facture - Brut'","Facture - Brute")
    gl['PieceRef'] = gl["PieceRef"].str.replace("T&E","VD")
    gl['PieceRef'] = gl["PieceRef"].str.replace("Inv","Facture")
    gl['PieceRef'] = gl["PieceRef"].str.replace("RECUR DEF RENT","LOCATION DIFFÉRÉE RECUR")
    


    gl['PieceRef'] = gl["PieceRef"].str.replace(" NaT ","")
    gl['JournalLib'] = gl["JournalLib"].str.replace(" NaT ","")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace(" NaT ","")

    gl['PieceRef'] = gl["PieceRef"].str.replace(" NAN ","")
    gl['JournalLib'] = gl["JournalLib"].str.replace(" NAN ","")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace(" NAN ","")

    gl['PieceRef'] = gl["PieceRef"].str.replace(" nan ","")
    gl['JournalLib'] = gl["JournalLib"].str.replace(" nan ","")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace(" nan ","")

    gl['PieceRef'] = gl["PieceRef"].str.replace(" nannan ","")
    gl['JournalLib'] = gl["JournalLib"].str.replace(" nannan ","")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace(" nannan ","")
    
    gl.loc[gl["JournalLib"].str.isnumeric(),'JournalLib'] = gl['JournalCode']
    gl['JournalLib'] = gl['JournalLib'].replace(codes)
    gl['JournalLib'] = gl["JournalLib"].str.replace("-2014123456789","-2014V")

    gl['JournalLib'] = gl["JournalLib"].str.replace("T/&E","VD")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("T/&E","VD")
    
    gl['DocDate'] = gl['Document Date']
    
    gl.loc[gl["PieceRef"].isnull(),'PieceRef'] = gl["JournalLib"].map(str) + " " + gl.DocDate.dt.strftime('%Y%m%d').astype(str)
    gl.loc[gl["EcritureLib"].str.isnumeric(),'EcritureLib'] = gl['JournalLib'].map(str) + gl['EcritureNum'].map(str)

    gl['Document Date'] = gl['DocDate']
    del gl['DocDate']
    gl['EcritureLib'] = gl['EcritureLib'].apply(lambda x: x.upper())
    gl['JournalLib'] = gl['JournalLib'].apply(lambda x: x.upper())
    gl['PieceRef'] = gl['PieceRef'].apply(lambda x: x.upper())
    gl['Credit'] = gl['Credit'].abs()
    gl = gl.sort_values('EcritureNum')

    gl.loc[gl["EcritureLib"].str.isnumeric(),'EcritureLib'] = gl['JournalLib']
    gl.loc[gl["EcritureLib"].str.startswith('5'),'EcritureLib'] = gl['JournalLib']


    gl['EcritureLib'] = gl['EcritureLib'].str.replace('^\d+','')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("^\s+","")
    gl['EcritureLib'] = gl["EcritureLib"].str.replace("^\W+","")

    gl['EcritureLib'] = gl["EcritureLib"].str.replace('CLEANING SERVICES', 'SERVICES DE NETTOYAGE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('DUTIES', 'DROITS')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('PARISLOCATION', 'PARIS LOCATION')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('FACTURE BRUTEE', 'FACTURE BRUTE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('SECURITE SOCIALE  CONTRIBUTIONS A LA FOURMATION', 'SECURITE SOCIALE CONTRIBUTIONS A LA FOURMATION')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('SECURITE SOCIALE  CONTRI APPRENTISSAGE', 'SECURITE SOCIALE CONTRI APPRENTISSAGE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('PENSION  COTISATIONS DE RETRAITE REUNICA', 'PENSION COTISATIONS DE RETRAITE REUNICA')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('REPAS DE TRAVAIL  EMPLOYE ITINERANT DE DOLBY ', 'REPAS DE TRAVAIL EMPLOYE ITINERANT DE DOLBY ')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('SANTE PRIVEE  ASSURANCE MEDICALE AXA', 'SANTE PRIVEE ASSURANCE MEDICALE AXA')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('PENSION  ASSURANCE VIE ET INVALIDITE', 'PENSION ASSURANCE VIE ET INVALIDITE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('UNSUBMITTEDUNPOSTED', 'NON SOUMIS ET NON ATTRIBUE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('WIRE', 'VIREMENT')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('LAUNDRY', 'BLANCHISSERIE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('D’', ' ')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('T B I', 'TBI')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('QUARTERLY CONTROL VISIT', 'VISITE DE CONTROLE TRIMESTRIELLE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('PASSPORTSVISA FRAIS', 'FRAIS DE VISA')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('CAR RENTAL', 'LOCATION DE VOITURE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('BENEFITS CONSULTING SERVICES', 'AVANTAGES SERVICES DE CONSULTANT')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('RECEIPT AND POLICY', 'RÉCEPTION ET POLITIQUE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('MEMBERSHIP', 'ABONNEMENT')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('ER APPREN  CONTRI', 'CONTRI DE FORMATION')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('STATEMENT', 'RELEVÉ BANCAIRE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('CAFES FOLLIET FOURNITURES DE CAFEVAL2400', 'FOLLIET DE CAFE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('ACCR JULSEP18', 'ACCUM JUL SEP18')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('FACTUREALIDITE', 'INVALIDITE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('BON DEJEUNERRETENUE', 'BON DEJEUNER RETENUE')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('CASH', 'ARGENT')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('UNSUBMITTEDUNPOSTED', 'NON-SOUMIS')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('AVRILJUILLET', 'AVRIL JUILLET')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('V2', ' AJUSTMENTS ')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('ANNUAL MAINTENANCE', 'MAINTENANCE ANNUELLE')
    
    return gl

def replace(gl):

    gl = gl.replace([' & '],[' ET '])
    gl = gl.replace(['&'],[' ET '])

    gl['EcritureLib'] = gl["EcritureLib"].str.replace('É', 'E')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('Ô', 'O')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('À', 'A')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('È', 'E')
    gl['EcritureLib'] = gl["EcritureLib"].str.replace('Û', 'U')

    gl['PieceRef'] = gl["PieceRef"].str.replace('É', 'E')
    gl['PieceRef'] = gl["PieceRef"].str.replace('Ô', 'O')
    gl['PieceRef'] = gl["PieceRef"].str.replace('À', 'A')
    gl['PieceRef'] = gl["PieceRef"].str.replace('È', 'E')
    gl['PieceRef'] = gl["PieceRef"].str.replace('Û', 'U')

    gl['JournalLib'] = gl["JournalLib"].str.replace('É', 'E')
    gl['JournalLib'] = gl["JournalLib"].str.replace('Ô', 'O')
    gl['JournalLib'] = gl["JournalLib"].str.replace('À', 'A')
    gl['JournalLib'] = gl["JournalLib"].str.replace('È', 'E')
    gl['JournalLib'] = gl["JournalLib"].str.replace('Û', 'U')

    gl['EcritureLib'] = gl["EcritureLib"].str.replace('^\d+',' ')
    gl['PieceRef'] = gl["PieceRef"].str.replace('^\d+',' ')
    gl['JournalLib'] = gl["JournalLib"].str.replace('^\d+',' ')

    gl['EcritureLib'] = gl['EcritureLib'].str.replace('[^A-Za-z0-9-\s]+', '')
    gl['JournalLib'] = gl['JournalLib'].str.replace('[^A-Za-z0-9-\s]+', '')
    gl['PieceRef'] = gl['PieceRef'].str.replace('[^A-Za-z0-9-\s]+', '')


    gl.loc[gl["EcritureLib"].str.startswith('MB'),'EcritureLib'] = 'FACTURE COUPA'
    gl.loc[gl["EcritureLib"].str.startswith('MK'),'EcritureLib'] = 'FACTURE COUPA'
    gl["EcritureLib"] = gl["EcritureLib"].str.replace('WORKING REPAS','REPAS DE TRAVAIL')
    gl.loc[gl["EcritureLib"].str.startswith('AF'),'EcritureLib'] = 'DEPRECIATION DE' + gl['CompteLib'].astype(str)

    gl['JournalLib'] = gl['JournalLib'].str.replace('^\s+', '')
    gl['PieceRef'] = gl['PieceRef'].str.replace('^\s+', '')
    gl['EcritureLib'] = gl['EcritureLib'].str.replace('^\s+', '')

    gl.loc[gl["JournalLib"].str.isnumeric(),'JournalLib'] = gl['JournalCode']

    codes = pd.read_excel('mapping-journal.xlsx')
    codes = codes.set_index('JournalCode').to_dict()["JournalLib_FR"]
    gl['JournalLib'] = gl['JournalLib'].replace(codes)

    gl.loc[gl["EcritureLib"].str.isnumeric(),'EcritureLib'] = gl['JournalLib']
    gl.loc[gl["PieceRef"].isnull(),'PieceRef'] = gl['JournalLib']

    
    

    return gl

def delete_old(gl, current):

    prev = int(current) - 1

    gl['EcritureDate'] = pd.to_datetime(gl['EcritureDate'],format='%d%m%Y')
    gl[(gl['EcritureDate'].dt.year >= prev)]
    gl[(gl['EcritureDate'].dt.year == current) | (gl['EcritureDate'].dt.month > 9)]
    

    return gl

def save_results(gl, output):

    gl['EcritureLib'] = gl['EcritureLib'].apply(lambda x: x.upper())
    gl['JournalLib'] = gl['JournalLib'].apply(lambda x: x.upper())
    gl['PieceRef'] = gl['PieceRef'].apply(lambda x: x.upper())

    
    del gl['Amount in doc. curr.']
    del gl['Assignment']
    del gl['Document Date']
    del gl['Reference']
    del gl['Text']
    del gl['Posting Date']
    del gl['Document Number']
    del gl['Document Type']
    del gl['Document currency']
    del gl['G/L Account']
    del gl['Local Currency']
    del gl['Local currency 2']
    del gl['Offsetting acct no.']
    del gl['Entry Date']
    del gl['Document Header Text']
    del gl['Amount in loc.curr.2']

     
    writer = pd.ExcelWriter(output,
                            engine='xlsxwriter',
                            datetime_format='yyyymmdd',
                            date_format='yyyymmdd')

    gl.to_excel(writer, index = False,sheet_name = ('Sheet 1'), columns =['JournalCode','JournalLib','EcritureNum','EcritureDate','CompteNum',
                                                                'CompteLib','CompAuxNum','CompAuxLib','PieceRef','PieceDate','EcritureLib',
                                                                'Debit','Credit','EcritureLet','DateLet','ValidDate','MontantDevise','ldevise'])


    workbook  = writer.book
    worksheet = writer.sheets['Sheet 1']
    worksheet.set_column('A:AV', 40)
    writer.save()

    return gl

def save_as_text(df, c):
    
    df_text = df.to_csv(c, index = False, sep = "|", na_rep = " ", date_format = "%Y/%m/%d", encoding="utf-8-sig")
     
    return df_text


if __name__ == '__main__':
    args = parse_args()

    current = args.Financial_Year
    gl_items = args.GL
    parked = args.Parked
    output_file = args.Excel_File
    output2 = args.Text_File
    carry1 = args.Carryforwards

    first_df = carry(carry1)
    output_df = combine(gl_items,parked, first_df)
    output_df_transformed = transform(output_df)
    output_df_translated = translate(output_df_transformed)
    out_replace = replace(output_df_translated)

    deleted_dates = delete_old(out_replace, current)
    output_df_saved = save_results(deleted_dates,output_file)
    
    save_as_text(output_df_saved,output2)
    
    z = output_df_saved['Debit'].sum(axis = 0,skipna = True)
    y = output_df_saved['Credit'].sum(axis = 0, skipna = True)
    h = z - y
    if h != 0:
        print("WARNING: Debits and Credits are not balanced!")
