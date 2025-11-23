Smart Agriculture Weather-Based Reminder & Tracking System

WeatherTech is an intelligent agricultural tracking application designed to simplify farmers' daily tasks. It automatically collects weather data, tracks fertilization and pesticide schedules, allows setting custom reminders, and presents all information through a modern interface.

The application is a Windows desktop software built with CustomTkinter + Selenium.

🚀 Features

🌤️ Real-Time Weather Data

    Automatic data retrieval via Selenium from MGM

    Measures temperature, rainfall, humidity, wind speed, altitude, sunrise & sunset, and 8 other parameters

    Automatic refresh system

⏰ Smart Reminder System

    Custom conditions for each weather parameter: below, above, equal

    Daily / weekly / monthly recurrence

    Active/inactive reminder control

    Audio notification on alert

🌱 Agriculture Task Tracking

    Track fertilization and pesticide schedules

    Automatic remaining days calculation

    JSON-based data storage

📅 Interactive Calendar

    Custom calendar UI with tkcalendar

    Marks fertilization and pesticide dates

    Shows details on date click

💾 Backup & Restore

    One-click data export

    Restore from backup

🛠️ Technologies Used

    Python 3

    Tkinter & CustomTkinter — modern GUI

    Selenium — MGM weather data retrieval

    ttkthemes — theme engine

    tkcalendar — calendar widget

    winsound — notification sounds

    JSON — data storage

    threading — background tasks

    logging — error & info logging

⚡ How to Use

    Clone the repository

    git clone https://github.com/asilgumus/WeatherTech
    cd WeatherTech


    Install dependencies

    pip install -r requirements.txt


    Set up ChromeDriver
    Selenium requires ChromeDriver. Download the version matching your Chrome browser:
    https://googlechromelabs.github.io/chrome-for-testing/

    And add it to your PATH.

    Run the application

    python main.py


🧑‍💻 Developer

Asil Doğan Gümüş
GitHub: https://github.com/asilgumus

⭐ Support

If you like the project, please give the repo a ⭐.

📄 License

This project is licensed under the MIT License
