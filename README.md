# sgdatabot
Telegram chatbot serving various data and alerts based on Singapore Government public data sources, such as 
[Data.gov.sg](https://data.gov.sg/) and [LTA DataMall](https://www.mytransport.sg/content/mytransport/home/dataMall.html).

*Tested on Python 2.7 and Python 3.7.*

## Installation
You will need the following Python packages:
* [telepot](https://telepot.readthedocs.io/en/latest/)
* [dataset](https://dataset.readthedocs.io/en/latest/)
* [geopy](https://geopy.readthedocs.io/en/stable/)
* [SVY21](https://github.com/cgcai/SVY21): The Python file `SVY21.py` has been included in this repository.
* [requests](https://pypi.org/project/requests/)
* [supervisor](http://supervisord.org/installing.html) (Optional): *supervisor* would help to run this project as a background process 
and offers feartures such as restarting upon crash. The configuration will be covered below.

It is recommended to setup up a 
[Python virtual environment](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)
for installing the dependency packages and running this project.

## Configuration
Before running the project, there are some configurations to be performed. 

### Obtaining tokens and keys

#### Creating a Telegram bot
In order to host this project as a Telegram chatbot, you will have to 
[create a bot with BotFather](https://core.telegram.org/bots#3-how-do-i-create-a-bot)
and obtain a bot token that is registered to your unique bot name. Your *bot name* and *bot token* will be required in a later 
configuration step.

#### Requesting for API access to Data.gov.sg
In order request for data from Data.gov.sg, you will have to
[request for API access](https://data.gov.sg/developer) and obtain an *API token*, 
which will be required in a later configuration step. Please subscribe to the mailing list to
be notified of any API offline and maintanence periods, which will result in certain features of this chatbot to be unavailable.

#### Requesting for API access to LTA DataMall
In order request for data from LTA DataMall, you will have to
[request for API access](https://www.mytransport.sg/content/mytransport/home/dataMall/request-for-api.html) and obtain an *API token*, 
which will be required in a later configuration step. Please use a valid email as DataMall in order to obtain the API token as well as
be notified of any API offline and maintanence periods, which will result in certain features of this chatbot to be unavailable.

### Inserting tokens and keys
Modify `SGdataBot.py` and replace the placeholder names with your Telegram *bot name*, Telegram *bot token*,
*API tokens and keys* obtained earlier accordingly.
```bash
BOT_NAME = "@YOUR_BOT_NAME"
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN
DATAGOV_API_KEY = "YOUR_DATAGOV_API_KEY"
DATAMALL_TOKEN = "YOUR_DATAMALL_TOKEN"
```

Modify `ltadatamall_updatecache.py` and replace the placeholder name with your LTA DataMall *API token* obtained earlier.
```bash
DATAMALL_TOKEN = "YOUR_DATAMALL_TOKEN"
```

## Run
At this point, you should be able to execute `SGdataBot.py` and run this project as a Telegram chatbot.
```bash
python3 SGdataBot.py
```

## Running as a background process
You may wish to run this project as a background process so that the chatbot can be available 24/7.

### Setting up supervisor on Linux (Optional)
A recommended method of running this project as a background process is to use [supervisor](http://supervisord.org/).
After [installing supervisor](http://supervisord.org/installing.html), you will have to create a configuration file for a new process.
Create `SGdataBot.conf` with the contents of the following code segment and place it in `/etc/supervisor/conf.d`. 
Replace `/path/to/project/` with the path to the location of this project.
```bash
[program:SGdataBot]
command=python3 /path/to/project/SGdataBot.py
directory=/path/to/project
autostart=true
autorestart=true
startretries=3
stderr_logfile=/path/to/project/SGdataBot.err.log
stdout_logfile=/path/to/project/SGdataBot.out.log
user=root
environment= 
```
After creating the configuration file, execute the following commands to reload the confgurations in the supervisor daemon
and start the chatbot as a process.
```bash
supervisorctl reread
supervisorctl update
supervisorctl start SGdataBot
```



