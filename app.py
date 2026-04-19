"""
Weather App with GUI
--------------------
Features:
1. Current weather for any city
2. Hourly weather sequence through today
3. Weekly forecast for any selected day

Uses:
- Tkinter (built-in GUI)
- Open-Meteo API (free, no API key needed)
- Geocoding API (to convert city name -> coordinates)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.parse
import json
from datetime import datetime


# ---------- Weather code -> description + emoji ----------
WEATHER_CODES = {
    0:  ("Clear sky", "☀️"),
    1:  ("Mainly clear", "🌤️"),
    2:  ("Partly cloudy", "⛅"),
    3:  ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    61: ("Slight rain", "🌦️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Slight snow", "🌨️"),
    73: ("Moderate snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Rain showers", "🌦️"),
    81: ("Moderate showers", "🌧️"),
    82: ("Violent showers", "⛈️"),
    85: ("Snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm w/ hail", "⛈️"),
    99: ("Severe thunderstorm", "⛈️"),
}


def describe_weather(code):
    return WEATHER_CODES.get(code, ("Unknown", "❓"))


# ---------- API helpers ----------
def http_get_json(url):
    """Simple helper to fetch JSON from a URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "WeatherApp/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geocode_city(city):
    """Turn a city name into latitude/longitude using Open-Meteo's geocoding API."""
    params = urllib.parse.urlencode({"name": city, "count": 1, "language": "en", "format": "json"})
    url = f"https://geocoding-api.open-meteo.com/v1/search?{params}"
    data = http_get_json(url)
    results = data.get("results")
    if not results:
        return None
    r = results[0]
    return {
        "name": r.get("name"),
        "country": r.get("country", ""),
        "latitude": r["latitude"],
        "longitude": r["longitude"],
        "timezone": r.get("timezone", "auto"),
    }


def fetch_weather(lat, lon, timezone="auto"):
    """Fetch current, hourly, and daily forecast."""
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,apparent_temperature",
        "hourly": "temperature_2m,weather_code,precipitation_probability",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
        "timezone": timezone,
        "forecast_days": 7,
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    return http_get_json(url)


# ---------- Main app ----------
class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Weather App")
        self.geometry("780x620")
        self.configure(bg="#1e2a3a")

        self.weather_data = None
        self.location = None

        self._build_ui()

    def _build_ui(self):
        # --- Top: search bar ---
        top = tk.Frame(self, bg="#1e2a3a")
        top.pack(fill="x", padx=20, pady=15)

        tk.Label(top, text="City:", fg="white", bg="#1e2a3a",
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0, 8))

        self.city_entry = tk.Entry(top, font=("Segoe UI", 12), width=30)
        self.city_entry.pack(side="left", padx=(0, 8))
        self.city_entry.bind("<Return>", lambda e: self.search_weather())

        tk.Button(top, text="Search", command=self.search_weather,
                  bg="#3a86ff", fg="white", font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=15, cursor="hand2").pack(side="left")

        # --- Current weather section ---
        self.current_frame = tk.Frame(self, bg="#2a3a52", bd=0)
        self.current_frame.pack(fill="x", padx=20, pady=10)

        self.city_label = tk.Label(self.current_frame, text="Enter a city to start",
                                    fg="white", bg="#2a3a52",
                                    font=("Segoe UI", 16, "bold"))
        self.city_label.pack(pady=(12, 4))

        self.temp_label = tk.Label(self.current_frame, text="—",
                                    fg="#ffd166", bg="#2a3a52",
                                    font=("Segoe UI", 28, "bold"))
        self.temp_label.pack()

        self.cond_label = tk.Label(self.current_frame, text="",
                                    fg="white", bg="#2a3a52",
                                    font=("Segoe UI", 13))
        self.cond_label.pack()

        self.details_label = tk.Label(self.current_frame, text="",
                                       fg="#cfd8dc", bg="#2a3a52",
                                       font=("Segoe UI", 10))
        self.details_label.pack(pady=(4, 12))

        # --- Tabs: Today hourly & Weekly forecast ---
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        self.hourly_tab = tk.Frame(self.tabs, bg="#1e2a3a")
        self.weekly_tab = tk.Frame(self.tabs, bg="#1e2a3a")
        self.tabs.add(self.hourly_tab, text="Today (Hourly)")
        self.tabs.add(self.weekly_tab, text="Weekly Forecast")

        self._build_hourly_tab()
        self._build_weekly_tab()

    def _build_hourly_tab(self):
        # Scrollable list of hours
        container = tk.Frame(self.hourly_tab, bg="#1e2a3a")
        container.pack(fill="both", expand=True, padx=5, pady=5)

        self.hourly_canvas = tk.Canvas(container, bg="#1e2a3a", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.hourly_canvas.yview)
        self.hourly_inner = tk.Frame(self.hourly_canvas, bg="#1e2a3a")

        self.hourly_inner.bind(
            "<Configure>",
            lambda e: self.hourly_canvas.configure(scrollregion=self.hourly_canvas.bbox("all"))
        )

        self.hourly_canvas.create_window((0, 0), window=self.hourly_inner, anchor="nw")
        self.hourly_canvas.configure(yscrollcommand=scrollbar.set)

        self.hourly_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scroll
        self.hourly_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.hourly_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        )

        self.hourly_placeholder = tk.Label(
            self.hourly_inner, text="Search a city to see today's hourly forecast.",
            fg="#90a4ae", bg="#1e2a3a", font=("Segoe UI", 11)
        )
        self.hourly_placeholder.pack(pady=20)

    def _build_weekly_tab(self):
        top = tk.Frame(self.weekly_tab, bg="#1e2a3a")
        top.pack(fill="x", padx=10, pady=10)

        tk.Label(top, text="Pick a day:", fg="white", bg="#1e2a3a",
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 8))

        self.day_combo = ttk.Combobox(top, state="readonly", width=30, font=("Segoe UI", 10))
        self.day_combo.pack(side="left")
        self.day_combo.bind("<<ComboboxSelected>>", self._show_selected_day)

        self.day_detail = tk.Frame(self.weekly_tab, bg="#2a3a52")
        self.day_detail.pack(fill="x", padx=10, pady=10)

        self.day_detail_label = tk.Label(
            self.day_detail, text="Search a city, then pick a day from the dropdown.",
            fg="#cfd8dc", bg="#2a3a52", font=("Segoe UI", 11), justify="left"
        )
        self.day_detail_label.pack(padx=15, pady=15, anchor="w")

        # Full week at a glance
        self.week_grid = tk.Frame(self.weekly_tab, bg="#1e2a3a")
        self.week_grid.pack(fill="both", expand=True, padx=10, pady=5)

    # ---------- Actions ----------
    def search_weather(self):
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showwarning("Missing city", "Please type a city name.")
            return

        try:
            loc = geocode_city(city)
            if not loc:
                messagebox.showerror("Not found", f"Could not find the city: {city}")
                return

            data = fetch_weather(loc["latitude"], loc["longitude"], loc["timezone"])
            self.location = loc
            self.weather_data = data

            self._update_current()
            self._update_hourly()
            self._update_weekly()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch weather:\n{e}")

    def _update_current(self):
        loc = self.location
        cur = self.weather_data["current"]
        code = cur["weather_code"]
        desc, icon = describe_weather(code)

        title = f"{loc['name']}, {loc['country']}"
        self.city_label.config(text=title)
        self.temp_label.config(text=f"{icon}  {cur['temperature_2m']}°C")
        self.cond_label.config(text=desc)
        details = (
            f"Feels like {cur['apparent_temperature']}°C   •   "
            f"Humidity {cur['relative_humidity_2m']}%   •   "
            f"Wind {cur['wind_speed_10m']} km/h"
        )
        self.details_label.config(text=details)

    def _update_hourly(self):
        # Clear previous
        for widget in self.hourly_inner.winfo_children():
            widget.destroy()

        hourly = self.weather_data["hourly"]
        times = hourly["time"]
        temps = hourly["temperature_2m"]
        codes = hourly["weather_code"]
        precip = hourly["precipitation_probability"]

        # Only show today's hours
        today = datetime.now().date().isoformat()
        header = tk.Label(
            self.hourly_inner,
            text=f"Hourly forecast for today ({today})",
            fg="white", bg="#1e2a3a", font=("Segoe UI", 12, "bold")
        )
        header.pack(pady=(5, 10))

        count = 0
        for t, temp, code, pp in zip(times, temps, codes, precip):
            if not t.startswith(today):
                continue
            count += 1
            desc, icon = describe_weather(code)
            hour = t.split("T")[1]

            row = tk.Frame(self.hourly_inner, bg="#2a3a52")
            row.pack(fill="x", padx=10, pady=3)

            tk.Label(row, text=hour, fg="#ffd166", bg="#2a3a52",
                     font=("Segoe UI", 11, "bold"), width=8).pack(side="left", padx=8, pady=6)
            tk.Label(row, text=icon, bg="#2a3a52",
                     font=("Segoe UI", 14), width=3).pack(side="left")
            tk.Label(row, text=f"{temp}°C", fg="white", bg="#2a3a52",
                     font=("Segoe UI", 11), width=8).pack(side="left")
            tk.Label(row, text=desc, fg="#cfd8dc", bg="#2a3a52",
                     font=("Segoe UI", 10), width=22, anchor="w").pack(side="left")
            tk.Label(row, text=f"Rain: {pp}%", fg="#8ecae6", bg="#2a3a52",
                     font=("Segoe UI", 10)).pack(side="left", padx=10)

        if count == 0:
            tk.Label(self.hourly_inner, text="No hourly data available.",
                     fg="#90a4ae", bg="#1e2a3a", font=("Segoe UI", 11)).pack(pady=20)

    def _update_weekly(self):
        daily = self.weather_data["daily"]
        dates = daily["time"]
        codes = daily["weather_code"]
        tmax = daily["temperature_2m_max"]
        tmin = daily["temperature_2m_min"]
        pp = daily["precipitation_probability_max"]

        # Dropdown options
        options = []
        for d in dates:
            dt = datetime.fromisoformat(d)
            options.append(dt.strftime("%A, %b %d"))
        self.day_combo["values"] = options
        if options:
            self.day_combo.current(0)
            self._show_selected_day()

        # Clear week grid
        for widget in self.week_grid.winfo_children():
            widget.destroy()

        tk.Label(self.week_grid, text="Full week at a glance:",
                 fg="white", bg="#1e2a3a",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=5, pady=(5, 8))

        grid = tk.Frame(self.week_grid, bg="#1e2a3a")
        grid.pack(fill="x")

        for i, (d, c, hi, lo, p) in enumerate(zip(dates, codes, tmax, tmin, pp)):
            desc, icon = describe_weather(c)
            dt = datetime.fromisoformat(d)
            day_name = dt.strftime("%a %b %d")

            card = tk.Frame(grid, bg="#2a3a52", width=95, height=130)
            card.pack(side="left", padx=4, pady=2)
            card.pack_propagate(False)

            tk.Label(card, text=day_name, fg="#ffd166", bg="#2a3a52",
                     font=("Segoe UI", 9, "bold")).pack(pady=(8, 2))
            tk.Label(card, text=icon, bg="#2a3a52",
                     font=("Segoe UI", 20)).pack()
            tk.Label(card, text=f"{hi}° / {lo}°", fg="white", bg="#2a3a52",
                     font=("Segoe UI", 10, "bold")).pack(pady=(2, 0))
            tk.Label(card, text=desc, fg="#cfd8dc", bg="#2a3a52",
                     font=("Segoe UI", 8), wraplength=90).pack()
            tk.Label(card, text=f"🌧 {p}%", fg="#8ecae6", bg="#2a3a52",
                     font=("Segoe UI", 8)).pack(pady=(2, 6))

    def _show_selected_day(self, event=None):
        if not self.weather_data:
            return
        idx = self.day_combo.current()
        if idx < 0:
            return

        daily = self.weather_data["daily"]
        date = daily["time"][idx]
        code = daily["weather_code"][idx]
        hi = daily["temperature_2m_max"][idx]
        lo = daily["temperature_2m_min"][idx]
        pp = daily["precipitation_probability_max"][idx]
        desc, icon = describe_weather(code)

        dt = datetime.fromisoformat(date)
        pretty = dt.strftime("%A, %B %d, %Y")

        text = (
            f"{icon}   {pretty}\n\n"
            f"Conditions:  {desc}\n"
            f"High:  {hi}°C     Low:  {lo}°C\n"
            f"Chance of precipitation:  {pp}%"
        )
        self.day_detail_label.config(text=text, justify="left", font=("Segoe UI", 12))


if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()