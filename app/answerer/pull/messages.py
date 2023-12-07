MESSAGE_WELCOME = """\
Ciao, questa è la chat business di Weeklend.
Qua puoi inserire gli eventi che verranno poi mostrati ai nostri utenti.
Cercherò di darti una mano a estrarre le informazioni necessarie per \
registrare un evento correttamente.
Potresti iniziare descrivendomi la tua attività?\
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
