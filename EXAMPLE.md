# Exmaple Usage
The available commands and exmaple usage supported by this project's chatbot (Bot) are detailed below.

## Bus
Bus-related commands
* __/busstop [*bus_stop_code*]__: Gives summary information of the bus stop with *bus_stop_code*, including Bus stop name, 
Bus service numbers at that bus stop, and Bus arrival timings for the next 3 buses of each bus service.
* __/busarrive [*bus_stop_code*] [*bus_service_number*]__: Sets an alert to provide notification when Bus *bus_service_number* is
arriving to Bus Stop *bus_stop_code* in 1 minute.
* __/busalert [*bus_stop_code*] [*bus_service_number*] [*alert_minutes*]__: Sets an alert to provide notification when 
Bus *bus_service_number* is arriving to Bus Stop *bus_stop_code* in *alert_minutes* minutes.

## Train
Train-related commands
* __/train__: Provides current Train service status.
* __/subscribetrainalert__: Subscribe to alert notification service for train disruption occurrences.
* __/unsubscribetrainalert__: Unsubscribe to alert notification service for train disruption occurrences.

## Car
Car-related commands
* __/carpark__: Provides nearby carpark information, including Car park name, Distance away to carpark, Number of available lots, Free parking
period, and a Google Maps location link of the carpark.
Bot will prompt for your location and followed by a selection of distance to search (100m, 200m or 300m).
* __/traffic__: Provides nearby traffic camera images of road traffic with Traffic camera ID, Timing of photo, 
and Distance away to traffic camera.
Bot will prompt for your location and followed by a selection of distance to search (500m, 1km or 1.5km).

## Weather
Weather-related commands
* __/forecast [*area_name*]__: Provides weather forecast of *area_name* based on the nearest weather station.
Bot will prompt with list of possible areas if an invalid one is provided.
* __/forecastnearme__: Provides weather forecast of your location based on the nearest weather station.
Bot will prompt for your location.
* __/forecast24h__: Provides the latest 24-hour weather forecast.
* __/forecast4day__: Provides the latest 4-day weather forecast.
* __/psi [*area_name*]__: Provides PSI information of *area_name* based on the nearest weather station.
Bot will prompt with list of possible areas if an invalid one is provided.
* __/psinearme__: Provides PSI information of your location based on the nearest weather station.
Bot will prompt for your location.
* __/pm25 [*area_name*]__: Provides PM2.5 information of *area_name* based on the nearest weather station.
Bot will prompt with list of possible areas if an invalid one is provided.
* __/pm25nearme__: Provides PM2.5 information of your location based on the nearest weather station.
Bot will prompt for your location.
* __/temp__: Provided current temperature.
* __/subscriberainalert__: Subscribe to alert notification service for forecasts of areas in your alert list.
* __/unsubscriberainalert__: Unsubscribe to alert notification service for forecasts of areas in your alert list.
* __/rainalertadd [*area_name*]__: Adds *area_name* to your list of areas to subscribe for rain alert notification service.
* __/rainalertdelete [*area_name*]__: Removes *area_name* to your list of areas to subscribe for rain alert notification service.
* __/rainalertlist__: Provides your list of areas that are subscribed for rain alert notification service.

