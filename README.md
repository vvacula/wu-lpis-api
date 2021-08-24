# WU LPIS API

Eine Python API für das Lehrveranstaltungs- und Prüfungsinformationssystem (LPIS) der WU Wien "[LPIS](https://www.wu.ac.at/studierende/tools-services/lpis/)". Die API verwendet `python.mechanize` für das emulieren eines Webbrowser, zum Navigieren und Absenden von (Form) Requests

Diese API ist der Kern der [Flips Anwendung](https://flips.hofstaetter.io/). Siehe auch: [alexanderhofstaetter/flips](https://github.com/alexanderhofstaetter/flips)

## Dependencies

Siehe auch die `import` Anweisungen in der Definition der Klasse `WuLpisApi`. 

`pip install python-dateutil mechanize beautifulsoup4 argparse lxml`

## Authentifizierung

Entweder über die parameter `--username` und `--password` die Zugangsdaten übermitteln, oder alternativ ein Credentials File mit `--credfile` angeben.

Das credfile muss folgendes Format aufweisen.

```
username=_USER_
password=_PASS_
```

## API Aufruf (Beispiel)

`python api.py --username=_USER_ --password=_PASS_ --action=_ACTION_`

Folgende Methoden stehen zur Auswahl. Diese können mit dem Parameter `--action` angegeben werden. Alternativ kann auch direkt die Klasse importiert werden und eine neuees Objekt instanziert werden. Die Ergebnisse eines Aufrufs können entweder vom Rückgabewert der Methode, oder aus der Variable data abgefragt werden.

```
api = WuLpisApi(username, password)
api.infos()
print json.dumps(api.getResults())
print json.dumps(api.data)
``` 

### infos
Liefert alle vorhanden Daten zu Studienplanpunkten, möglichen und durchgeführten Anmeldungen und Infos zu den untergeordneten Lehrveranstaltungen

``` json
{
    "data": {
        "pp": {
            "121328": {
                "attempts": "0", 
                "attempts_max": "5", 
                "depth": 3, 
                "id": "121328", 
                "lv_status": "PI 1567 Langer H. · Wagner D. (Anmeldung 03.09.2018 15:00)", 
                "lv_url": "DLVO?ASPP=125001_123456;SPP=124328;F=;A=5;SH=123456;R=277879", 
                "lvs": {
                    "": {
                        "capacity": "50", 
                        "date_end": "09.10.2018 23:59", 
                        "free": "0", 
                        "id": "", 
                        "name": "Soziale Kompetenz", 
                        "prof": "Langer H. · Wagner D.", 
                        "registerd_at": "03.09.2018 15:00", 
                        "semester": "WS 2018", 
                        "status": "Anmeldung", 
                        "waitlist": "16"
                    }, 
                    "1568": {
                        "capacity": "50", 
                        "date_end": "11.09.2018 23:59", 
                        "free": "0", 
                        "id": "1568", 
                        "internal_id": "405890", 
                        "name": "Soziale Kompetenz", 
                        "prof": "Langer H. · Müllauer-Hager B.", 
                        "semester": "WS 2018", 
                        "status": "Anmeldung nicht möglich", 
                        "waitlist": "14"
                    },
                }
            }
        }
    }
}
```


### registration
Führt automatisch eine Anmeldung zu einer PI/LV durch. Hierbei wird genau 1 Sekunde vor Beginn der Request gestartet um optimale Chance auf einen LV Platz zu sichern.

Vor dem Start der Registrierung sollte die lokale Zeit mit dem Zeitserver der WU (`timeserver.wu.ac.at`) synchronisiert werden.

Dem Aufruf müssen noch die Parametr `-lv` und `-pp` für Lehrveranstaltung und Planpunkt hinzugefügt werden. Mit dem Parameter `-lv2` kann eine alternative LV Nummer angeben werden. Die Anmeldung für diese wird durchgeführt, falls für die 1. LV keine Plätze mehr frei sind, für die 2. LV aber schon. Sind beide voll wird ein Wartelisteneintrag für die 1. LV durchgeführt.

`python api.py -c=creds.txt -a=registration -pp=124216 -lv=1094 -lv2=1097`

```
init time: 2018-09-20 14:58:35.912778
logging in ...
waiting: 79.58 seconds (1.33 minutes)
waiting till: 1537448398.8 (20.09.2018 14:59:58)
triggertime: 1537448398.8
final open time start: 2018-09-20 14:59:58.802870
start request 2018-09-20 14:59:58.802923
parsing done 2018-09-20 15:00:00.364986
registration is not (yet) possibe, waiting ...
reloading page and waiting for form to be submittable
start request 2018-09-20 15:00:00.365017
final open time end: 2018-09-20 15:00:03.709196
registration is possible
end time: 2018-09-20 15:00:03.730826
submitting registration form
Die Anmeldung zur Veranstaltung 1094 wurde durchgeführt.
Frei: 19 / 25

```
### Single registration using course number
One can also use the Single registration where is only needed to fill up the course number and click on sign-up button.

A new parameter `-a=number_registration` does the trick. Then number of the course is needed `-lv` .

`python api.py -c=creds.txt -a=number_registration -lv=1234`

# Copyright & License

Copyright (c) 2018-2019 Alexander Hofstätter - Released under the [MIT license](LICENSE.md).