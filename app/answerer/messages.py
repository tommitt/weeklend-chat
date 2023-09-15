from app.constants import LIMIT_BLOCKS_PER_WEEK

MESSAGE_WELCOME = """\
Ciao! 👋 È un piacere conoscerti!
Ti trovi su Weeklend, il posto giusto per scoprire eventi e attività a Torino. \
Dimmi pure in chat che tipo di evento stai cercando e, se hai una data specifica in mente, \
fammelo sapere. Sono qui per aiutarti a trovare le migliori opzioni per te! 💪🎉\
"""

MESSAGE_NOTHING_RELEVANT = """\
Mi dispiace, sembra che al momento non ci siano eventi che corrispondano alle tue indicazioni. \
Ma niente paura, possiamo cercare qualcosa di diverso insieme!
Cosa ne dici di provare con una nuova ricerca? Sarà divertente! 😊🎉\
"""

MESSAGE_INVALID_QUERY = f"""\
Alcune domande sono fuori dal mio campo d'azione, e questa è una di quelle. 💔
Prova con qualcosa di diverso per scoprire i migliori eventi nella tua zona!

Inoltre, ricorda che siamo in fase beta e ciò significa che imponiamo un limite di {LIMIT_BLOCKS_PER_WEEK} messaggi non validi alla settimana. \
Quindi, scegli attentamente la prossima domanda in modo da poter continuare a esplorare insieme fino alla fine della settimana! 😄📅
"""

MESSAGE_WEEK_ANSWERS_LIMIT = """\
Grazie mille per usare Weeklend così assiduamente!
Siamo in fase di beta e al momento possiamo accettare solo {limit_per_week} richieste a settimana, \
ma stiamo lavorando duramente per ampliare la nostra portata e poter rispondere a tutte le richieste. \
Sarà presto ancora più facile e divertente pianificare le tue attività. Restiamo in contatto! 😊📆

Il blocco scadrà in data: {block_expires_at}\
"""

MESSAGE_WEEK_BLOCKS_LIMIT = """\
Oh no! Sembra che tu abbia raggiunto il limite di {limit_per_week} messaggi non validi per questa settimana.
Non ti preoccupare, tornerò in data {block_expires_at} con nuovi suggerimenti per te. \
Ci vediamo presto! 😊🕒\
"""

MESSAGE_REACHED_MAX_USERS = """\
Ciao! 👋 Grazie mille per avermi contattato e per il tuo interesse in Weeklend! \
Siamo felici di vedere tanta richiesta, ma al momento abbiamo raggiunto il limite di utenti previsti per la beta. \
Ma non disperare! Stiamo lavorando duramente per aprire presto a nuovi utenti \
e darti la possibilità di scoprire fantastici eventi.
Resta con noi, torneremo presto con nuove opportunità! 🎉\
"""

MESSAGE_GOT_UNBLOCKED = """\
Che bello rivederti! \
Posso nuovamente rispondere alle tue domande e cercare le migliori opzioni per te! \
Avanti, cosa vorresti chiedermi oggi? 😄🎉\
"""
