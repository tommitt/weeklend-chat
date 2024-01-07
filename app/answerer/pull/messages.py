MESSAGE_WELCOME = """\
Ciao, questa è la chat business di Weeklend.
Qua puoi inserire le informazioni dei tuoi eventi che verranno poi \
mostrati agli utenti.
Cercherò di darti una mano a estrarre le informazioni necessarie \
per registrare un evento correttamente, ma come prima cosa ho bisogno \
che tu descriva l'attività che rappresenti e che ospita l'evento. 
L'attività viene registrata una sola volta, e una volta fatto, \
procederemo a registrare ogni evento successivo. 
Inizia pure a descrivermi l'attività!\
"""

MESSAGE_NOT_DELIVERED = """\
Perdonami, ma qualcosa è andato storto e non sono stato in grado di \
elaborare l'ultimo messaggio.\
"""

MESSAGE_UPDATED_BUSINESS = """\
La registrazione della tua attività è stata completata con successo:
- Nome: {name}
- Descrizione: {description}

Adesso puoi procedere nel registare un evento!\
"""

MESSAGE_REGISTERED_EVENT = """\
La registrazione dell'evento è stata completata con successo:
- Nome: {name}
- Descrizione: {description}
- URL: {url}
- Data di inizio: {start_date}
- Data di fine: {end_date}
- Luogo: {location}
- Diurno/notturno: {time_of_day}\
"""

MESSAGE_URL_NOT_PROVIDED = """\
Per procedere con la registrazione è necessario che tu fornisca \
un URL che rimandi a un sito esterno in cui si possono trovare \
ulteriori informazioni sull'evento.\
"""
