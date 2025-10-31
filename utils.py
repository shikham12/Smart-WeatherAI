import os
import requests
from geopy.geocoders import Nominatim
from dotenv import load_dotenv
load_dotenv()

OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")
USER_AGENT = os.getenv("USER_AGENT", "weather-app")

geolocator = Nominatim(user_agent=USER_AGENT, timeout=10)

def geocode_location(query):
    # try direct geocode (handles city, zip, landmark)
    try:
        location = geolocator.geocode(query, addressdetails=True, exactly_one=True)
        if location:
            name = location.address
            return {"name": name, "lat": location.latitude, "lon": location.longitude}
    except Exception as e:
        print("Geocode error:", e)
    return None

def reverse_geocode(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True)
        if location:
            return {"name": location.address, "lat": lat, "lon": lon}
    except Exception as e:
        print("Reverse geocode:", e)
    return None

def get_weather(lat, lon, units="metric", start_date=None, end_date=None):
    
    # Current weather
    current_url = f"https://api.openweathermap.org/data/2.5/weather"
    current_params = {"lat": lat, "lon": lon, "units": units, "appid": OPENWEATHER_KEY}
    
    # 5-day forecast
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast"
    forecast_params = {"lat": lat, "lon": lon, "units": units, "appid": OPENWEATHER_KEY}
    
    try:
        # Get current weather
        current_r = requests.get(current_url, params=current_params, timeout=10)
        current_r.raise_for_status()
        current_data = current_r.json()
        
        # Get forecast
        forecast_r = requests.get(forecast_url, params=forecast_params, timeout=10)
        forecast_r.raise_for_status()
        forecast_data = forecast_r.json()
        
        # Transform to match the expected format
        result = {
            "current": {
                "dt": current_data["dt"],
                "temp": current_data["main"]["temp"],
                "feels_like": current_data["main"]["feels_like"],
                "humidity": current_data["main"]["humidity"],
                "pressure": current_data["main"]["pressure"],
                "visibility": current_data.get("visibility", 10000) / 1000,  # Convert to km
                "wind_speed": current_data.get("wind", {}).get("speed", 0),
                "weather": current_data["weather"],
                "description": current_data["weather"][0]["description"] if current_data["weather"] else "N/A",
                "main": current_data["weather"][0]["main"] if current_data["weather"] else "N/A"
            },
            "daily": [],
            "requested_start_date": start_date,
            "requested_end_date": end_date
        }
        
        # Process forecast data to get daily summaries
        daily_temps = {}
        from datetime import datetime, date
        
        for item in forecast_data["list"]:
            date_str = item["dt_txt"][:10]  # Get date part (YYYY-MM-DD)
            
            # If date range is specified, filter the forecast
            if start_date and end_date:
                try:
                    item_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if isinstance(start_date, str) else start_date
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if isinstance(end_date, str) else end_date
                    
                    # Skip dates outside the requested range
                    if item_date < start_date_obj or item_date > end_date_obj:
                        continue
                except:
                    pass  # If date parsing fails, include all data
            
            if date_str not in daily_temps:
                daily_temps[date_str] = {
                    "dt": item["dt"],
                    "temps": [item["main"]["temp"]],
                    "weather": item["weather"]
                }
            else:
                daily_temps[date_str]["temps"].append(item["main"]["temp"])
        
        # Convert to daily format (max 5 days due to API limitation)
        for i, (date_str, data) in enumerate(list(daily_temps.items())[:5]):
            result["daily"].append({
                "dt": data["dt"],
                "date": date_str,
                "temp": {
                    "min": min(data["temps"]),
                    "max": max(data["temps"]),
                    "day": sum(data["temps"]) / len(data["temps"]),  # average
                    "avg": sum(data["temps"]) / len(data["temps"])   # average (alias for compatibility)
                },
                "weather": data["weather"],
                "description": data["weather"][0]["description"] if data["weather"] else "N/A",
                "main_condition": data["weather"][0]["main"] if data["weather"] else "N/A"
            })
        
        return result
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise Exception(f"Invalid API key. Please check your OpenWeatherMap API key. Error: {e}")
        else:
            raise Exception(f"Weather API error: {e}")
    except Exception as e:
        raise Exception(f"Failed to fetch weather data: {e}")
    
from transformers import pipeline

# Initialize summarizer as None - will load on demand
summarizer = None

def get_summarizer():
    """Lazy load the summarizer model"""
    global summarizer
    if summarizer is None:
        try:
            summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        except Exception as e:
            print(f"Warning: Could not load AI model: {e}")
            summarizer = False  
    return summarizer if summarizer is not False else None

def ai_generate_summary(weather_data, city):
    """Generates a natural language summary from forecast data."""
    try:
        # Try to get the AI summarizer
        model = get_summarizer()
        if model is None:
            # Fallback to enhanced simple text summary if AI model unavailable
            return create_enhanced_summary(weather_data, city)
        
        # Work with the current data structure
        current = weather_data.get("current", {})
        daily_forecast = weather_data.get("daily", [])
        
        # Build a comprehensive context for AI summarization
        text = f"Weather analysis for {city}: "
        
        # Add current weather with more context
        if current:
            temp = current.get("temp", "N/A")
            feels_like = current.get("feels_like", temp)
            humidity = current.get("humidity", "N/A")
            desc = current.get("weather", [{}])[0].get("description", "unknown")
            
            text += f"Currently experiencing {desc} with actual temperature of {temp}°C (feels like {feels_like}°C) and {humidity}% humidity. "
        
        # Add trend analysis and recommendations
        if daily_forecast:
            temps = [day.get("temp", {}).get("day", 0) for day in daily_forecast if day.get("temp", {}).get("day")]
            if len(temps) >= 2:
                trend = "rising" if temps[-1] > temps[0] else "falling" if temps[-1] < temps[0] else "stable"
                text += f"Temperature trend is {trend} over the next few days. "
            
            # Add weather pattern analysis
            weather_types = [day.get("weather", [{}])[0].get("main", "").lower() for day in daily_forecast]
            rain_days = weather_types.count("rain")
            clear_days = weather_types.count("clear")
            
            if rain_days > 2:
                text += "Expect frequent rainfall, consider carrying an umbrella. "
            elif clear_days > 2:
                text += "Generally clear skies ahead, great for outdoor activities. "
        
        # Add daily forecast with insights
        for i, day in enumerate(daily_forecast[:5]):
            temp_min = day.get("temp", {}).get("min", "N/A")
            temp_max = day.get("temp", {}).get("max", "N/A")
            desc = day.get("weather", [{}])[0].get("description", "unknown")
            
            if i == 0:
                text += f"Today: {desc} with temperatures ranging from {temp_min}°C to {temp_max}°C. "
            elif i == 1:
                text += f"Tomorrow: {desc}, expect {temp_min}°C to {temp_max}°C. "
            else:
                text += f"Day {i+1}: {desc} with range {temp_min}°C to {temp_max}°C. "

        # Ensure text is adequate for summarization
        if len(text.split()) < 15:
            return create_enhanced_summary(weather_data, city)
            
        summary = model(text, max_length=150, min_length=50, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        print("AI summary error:", e)
        return create_enhanced_summary(weather_data, city)

def create_enhanced_summary(weather_data, city):
    """Create an enhanced natural language summary without AI"""
    try:
        current = weather_data.get("current", {})
        daily_forecast = weather_data.get("daily", [])
        
        summary_parts = []
        
        # Current weather analysis
        if current:
            temp = current.get("temp", "N/A")
            feels_like = current.get("feels_like", temp)
            humidity = current.get("humidity", "N/A")
            desc = current.get("weather", [{}])[0].get("description", "unknown")
            
            # Temperature comfort analysis
            if isinstance(temp, (int, float)):
                if temp < 0:
                    comfort = "quite cold, bundle up!"
                elif temp < 10:
                    comfort = "chilly, wear a jacket"
                elif temp < 20:
                    comfort = "cool and comfortable"
                elif temp < 25:
                    comfort = "pleasant weather"
                elif temp < 30:
                    comfort = "warm and nice"
                else:
                    comfort = "quite hot, stay hydrated!"
            else:
                comfort = "moderate conditions"
            
            summary_parts.append(f"Right now in {city}, it's {desc} at {temp}°C ({comfort})")
            
            if isinstance(feels_like, (int, float)) and abs(feels_like - temp) > 3:
                summary_parts.append(f"though it feels like {feels_like}°C")
        
        # Forecast analysis
        if daily_forecast:
            temps = []
            weather_conditions = []
            
            for day in daily_forecast:
                day_temp = day.get("temp", {}).get("day")
                if day_temp is not None:
                    temps.append(day_temp)
                
                weather_main = day.get("weather", [{}])[0].get("main", "").lower()
                weather_conditions.append(weather_main)
            
            if temps:
                avg_temp = sum(temps) / len(temps)
                min_temp = min(temps)
                max_temp = max(temps)
                
                # Temperature trend analysis
                if len(temps) >= 2:
                    if temps[-1] > temps[0] + 2:
                        trend = "getting warmer"
                    elif temps[-1] < temps[0] - 2:
                        trend = "cooling down"
                    else:
                        trend = "staying fairly consistent"
                    
                    summary_parts.append(f"Over the next few days, temperatures will be {trend}")
                
                # Weather pattern insights
                rain_count = weather_conditions.count("rain")
                clear_count = weather_conditions.count("clear")
                cloud_count = weather_conditions.count("clouds")
                
                if rain_count >= 2:
                    summary_parts.append("with several rainy days expected - perfect time for indoor activities")
                elif clear_count >= 3:
                    summary_parts.append("with mostly clear skies - great for outdoor plans")
                elif cloud_count >= 2:
                    summary_parts.append("with cloudy conditions dominating the forecast")
                
                # Clothing recommendations
                if avg_temp < 5:
                    clothing = "Heavy winter clothing recommended"
                elif avg_temp < 15:
                    clothing = "Layers and a warm jacket would be ideal"
                elif avg_temp < 25:
                    clothing = "Light jacket or sweater should be sufficient"
                else:
                    clothing = "Light, breathable clothing recommended"
                
                summary_parts.append(f"Average temperature will be around {avg_temp:.1f}°C. {clothing}")
        
        # Combine all parts into a natural summary
        if summary_parts:
            return ". ".join(summary_parts) + "."
        else:
            return f"Weather information is available for {city}. Check the detailed forecast below for more insights."
            
    except Exception as e:
        print("Enhanced summary error:", e)
        return f"Weather data available for {city}. View the detailed forecast for current conditions and predictions."

def create_simple_summary(weather_data, city):
    """Create a simple text-based summary without AI"""
    try:
        current = weather_data.get("current", {})
        daily_forecast = weather_data.get("daily", [])
        
        summary = f"Weather summary for {city}: "
        
        if current:
            temp = current.get("temp", "N/A")
            desc = current.get("weather", [{}])[0].get("description", "unknown")
            summary += f"Currently {temp}°C with {desc}. "
        
        if daily_forecast:
            temps = []
            for day in daily_forecast:
                day_temp = day.get("temp", {}).get("day", None)
                if day_temp is not None:
                    temps.append(day_temp)
            
            if temps:
                avg_temp = sum(temps) / len(temps)
                summary += f"Average temperature for next few days: {avg_temp:.1f}°C."
        
        return summary
    except Exception as e:
        print("Simple summary error:", e)
        return f"Weather data available for {city}"

import requests
import re
from datetime import datetime, timedelta, date

class DynamicWeatherChatbot:
    """Advanced weather chatbot that uses real-time data for specific locations"""
    
    def __init__(self):
        self.openweather_key = os.getenv("OPENWEATHER_API_KEY", "fa3cf0f59b50581ae23ac3446a1bceba")
        self.geolocator = Nominatim(user_agent="dynamic-weather-chatbot", timeout=10)
    
    def get_weather_for_location(self, location_name):
        """Fetch real-time weather data for a specific location"""
        try:
            # Geocode the location
            location = self.geolocator.geocode(location_name, exactly_one=True)
            if not location:
                return None, f"Could not find location: {location_name}"
            
            lat, lon = location.latitude, location.longitude
            
            # Get current weather
            current_url = f"https://api.openweathermap.org/data/2.5/weather"
            current_params = {"lat": lat, "lon": lon, "units": "metric", "appid": self.openweather_key}
            
            # Get forecast
            forecast_url = f"https://api.openweathermap.org/data/2.5/forecast"
            forecast_params = {"lat": lat, "lon": lon, "units": "metric", "appid": self.openweather_key}
            
            current_r = requests.get(current_url, params=current_params, timeout=10)
            forecast_r = requests.get(forecast_url, params=forecast_params, timeout=10)
            
            if current_r.status_code != 200 or forecast_r.status_code != 200:
                return None, f"Could not fetch weather data for {location_name}"
            
            current_data = current_r.json()
            forecast_data = forecast_r.json()
            
            # Process the data
            weather_data = {
                "location": {
                    "name": location.address,
                    "lat": lat,
                    "lon": lon
                },
                "current": {
                    "dt": current_data["dt"],
                    "temp": current_data["main"]["temp"],
                    "feels_like": current_data["main"]["feels_like"],
                    "humidity": current_data["main"]["humidity"],
                    "pressure": current_data["main"]["pressure"],
                    "visibility": current_data.get("visibility", 0) / 1000,  # Convert to km
                    "wind_speed": current_data.get("wind", {}).get("speed", 0),
                    "weather": current_data["weather"],
                    "description": current_data["weather"][0]["description"],
                    "main": current_data["weather"][0]["main"]
                },
                "daily": []
            }
            
            # Process forecast data to get daily summaries
            daily_temps = {}
            for item in forecast_data["list"]:
                date = item["dt_txt"][:10]  # Get date part (YYYY-MM-DD)
                if date not in daily_temps:
                    daily_temps[date] = {
                        "dt": item["dt"],
                        "temps": [item["main"]["temp"]],
                        "weather": item["weather"],
                        "conditions": []
                    }
                else:
                    daily_temps[date]["temps"].append(item["main"]["temp"])
                
                daily_temps[date]["conditions"].append(item["weather"][0]["main"])
            
            # Convert to daily format
            for date, data in list(daily_temps.items())[:5]:
                # Most common weather condition for the day
                most_common_condition = max(set(data["conditions"]), key=data["conditions"].count)
                
                weather_data["daily"].append({
                    "date": date,
                    "dt": data["dt"],
                    "temp": {
                        "min": round(min(data["temps"]), 1),
                        "max": round(max(data["temps"]), 1),
                        "avg": round(sum(data["temps"]) / len(data["temps"]), 1)
                    },
                    "weather": data["weather"],
                    "main_condition": most_common_condition,
                    "description": data["weather"][0]["description"]
                })
            
            return weather_data, None
            
        except Exception as e:
            return None, f"Error fetching weather data: {str(e)}"
    
    def analyze_weather_context(self, weather_data, target_date=None):
        """Analyze weather data to provide context-aware insights"""
        current = weather_data["current"]
        daily = weather_data["daily"]
        location_name = weather_data["location"]["name"]

        # If a target_date is provided, use that day's forecast for analysis
        selected = None
        if target_date:
            if isinstance(target_date, date):
                target_str = target_date.isoformat()
            else:
                try:
                    target_str = str(target_date)
                except:
                    target_str = None

            if target_str:
                for d in daily:
                    if d.get('date') == target_str:
                        selected = d
                        break

        # Build base analysis using either the selected day or current conditions
        if selected:
            analysis = {
                "location": location_name,
                "current_temp": selected["temp"]["avg"],
                "feels_like": selected["temp"]["avg"],
                "condition": selected.get("description", selected.get('main_condition', 'N/A')),
                "main_condition": selected.get('main_condition', '').lower(),
                "humidity": weather_data.get('current', {}).get('humidity', None),
                "wind_speed": weather_data.get('current', {}).get('wind_speed', 0),
                "visibility": weather_data.get('current', {}).get('visibility', 0),
                "is_day": True,
                "analysis_date": selected.get('date')
            }
            temp = analysis["current_temp"]
        else:
            analysis = {
                "location": location_name,
                "current_temp": current["temp"],
                "feels_like": current["feels_like"],
                "condition": current["description"],
                "main_condition": current["main"].lower(),
                "humidity": current["humidity"],
                "wind_speed": current["wind_speed"],
                "visibility": current["visibility"],
                "is_day": self.is_daytime(current["dt"]),
                "analysis_date": None
            }
            temp = current["temp"]

        # Temperature comfort analysis
        if temp < 0:
            analysis["temp_comfort"] = "freezing"
        elif temp < 5:
            analysis["temp_comfort"] = "very_cold"
        elif temp < 10:
            analysis["temp_comfort"] = "cold"
        elif temp < 15:
            analysis["temp_comfort"] = "cool"
        elif temp < 20:
            analysis["temp_comfort"] = "mild"
        elif temp < 25:
            analysis["temp_comfort"] = "comfortable"
        elif temp < 30:
            analysis["temp_comfort"] = "warm"
        elif temp < 35:
            analysis["temp_comfort"] = "hot"
        else:
            analysis["temp_comfort"] = "very_hot"

        # Weather condition analysis
        condition_lower = analysis.get("main_condition", "").lower()
        if "rain" in condition_lower or "drizzle" in condition_lower:
            analysis["precipitation"] = "rainy"
        elif "snow" in condition_lower:
            analysis["precipitation"] = "snowy"
        elif "thunder" in condition_lower or "storm" in condition_lower:
            analysis["precipitation"] = "stormy"
        else:
            analysis["precipitation"] = "dry"

        # Add forecast trends
        if len(daily) >= 2:
            try:
                today_temp = daily[0]["temp"]["avg"]
                tomorrow_temp = daily[1]["temp"]["avg"]
                if tomorrow_temp > today_temp + 3:
                    analysis["temp_trend"] = "warming_up"
                elif tomorrow_temp < today_temp - 3:
                    analysis["temp_trend"] = "cooling_down"
                else:
                    analysis["temp_trend"] = "stable"
            except Exception:
                analysis["temp_trend"] = "stable"

        return analysis

    def is_daytime(self, timestamp):
        """Check if it's daytime based on timestamp"""
        hour = datetime.fromtimestamp(timestamp).hour
        return 6 <= hour <= 18

    def parse_location_and_date(self, message):
        """Extract location and date context from message"""
        location = None
        date_ctx = None

        # Extract location using regex
        m = re.search(r"\b(?:in|at|for|to)\s+([A-Za-z0-9\s,.'-]{2,60}?)(?=(?:\s+(?:today|tomorrow|on|this|next)\b)|[?.!,]|$)", message, re.I)
        if m:
            location = m.group(1).strip().strip(".,!?")

        # Extract date keywords
        if re.search(r"\btomorrow\b", message, re.I):
            date_ctx = date.today() + timedelta(days=1)
        elif re.search(r"\btoday\b", message, re.I):
            date_ctx = date.today()

        # Clean location of date words
        if location:
            location = re.sub(r"\b(today|tomorrow)\b", "", location, flags=re.I).strip()

        return location, date_ctx

    def get_response(self, message, location_name=None, date_context=None, start_date=None, end_date=None):
        """Generate dynamic response based on real weather data"""
        message = message.lower().strip()
        
        # Extract location and date from message if not provided
        if not location_name:
            loc, dt = self.parse_location_and_date(message)
            if loc:
                location_name = loc
            if dt and not date_context:
                date_context = dt

        # If start_date is provided, use it as the primary date context
        if start_date and not date_context:
            try:
                from datetime import datetime
                if isinstance(start_date, str):
                    date_context = datetime.strptime(start_date, '%Y-%m-%d').date()
                else:
                    date_context = start_date
            except:
                pass

        if not location_name:
            return "I'd be happy to help! Please specify a location, for example: 'What should I wear in Mumbai?' or 'Is it good weather for a picnic in Delhi?'"

        # Fetch real weather data with date range
        weather_data, error = self.get_weather_for_location_with_dates(location_name, start_date, end_date)
        if error:
            return f"Sorry, {error}. Please check the location name and try again."

        # Analyze the weather
        analysis = self.analyze_weather_context(weather_data, date_context)

        # Add date range information to responses if applicable
        date_info = ""
        if start_date and end_date:
            date_info = f" (for your selected period {start_date} to {end_date})"
        elif date_context:
            date_info = f" (for {date_context})"

        # Generate responses based on question type
        if any(word in message for word in ['wear', 'clothes', 'clothing', 'dress', 'outfit']):
            response = self.get_clothing_advice(analysis)
            return response + date_info
        
        elif any(word in message for word in ['rain', 'umbrella', 'wet', 'precipitation']):
            if analysis["precipitation"] in ["rainy", "stormy"]:
                return f"Yes! It's expected to be {analysis['condition']} in {analysis['location']}{date_info}. Definitely bring an umbrella or waterproof jacket. Temperature around {analysis['current_temp']}°C."
            else:
                return f"No rain expected in {analysis['location']}{date_info} - it should be {analysis['condition']} at around {analysis['current_temp']}°C. You can leave the umbrella at home!"
        
        elif any(word in message for word in ['activity', 'activities', 'do', 'picnic', 'outdoor', 'visit']):
            response = self.get_activity_advice(analysis)
            return response + date_info
        
        elif any(word in message for word in ['travel', 'drive', 'driving', 'flight', 'transport']):
            response = self.get_travel_advice(analysis)
            return response + date_info
        
        elif any(word in message for word in ['temperature', 'temp', 'hot', 'cold', 'warm']):
            return f"In {analysis['location']}{date_info}, expect around {analysis['current_temp']}°C (feels like {analysis['feels_like']}°C) with {analysis['condition']}. Humidity around {analysis['humidity']}% and wind speed {analysis['wind_speed']} m/s."
        
        elif any(word in message for word in ['forecast', 'tomorrow', 'next', 'future']):
            daily = weather_data.get("daily", [])
            
            # If user specified a date range, show forecast for that period
            if start_date and end_date and daily:
                forecast_summary = []
                for d in daily:
                    forecast_summary.append(f"{d.get('date')}: {d.get('description')} ({d['temp']['min']}°C-{d['temp']['max']}°C)")
                if forecast_summary:
                    return f"Forecast for {analysis['location']} from {start_date} to {end_date}: " + "; ".join(forecast_summary)
            
            # Standard forecast logic
            target_day = None
            if date_context:
                target_str = date_context.isoformat() if isinstance(date_context, date) else str(date_context)
                for d in daily:
                    if d.get('date') == target_str:
                        target_day = d
                        break

            if not target_day and re.search(r"\btomorrow\b", message, re.I) and len(daily) >= 2:
                target_day = daily[1]

            if target_day:
                return f"Forecast for {analysis['location']} on {target_day.get('date')}: {target_day.get('description')} with temperatures between {target_day['temp']['min']}°C and {target_day['temp']['max']}°C."

            if daily:
                summary = []
                for i, d in enumerate(daily[:3]):
                    day_label = 'Today' if i == 0 else 'Tomorrow' if i == 1 else f'Day {i+1}'
                    summary.append(f"{day_label}: {d.get('description')} ({d['temp']['min']}°C-{d['temp']['max']}°C)")
                return "Available forecast: " + "; ".join(summary)

            return f"I don't have the forecast for {analysis['location']} right now. Current conditions: {analysis['condition']} at {analysis['current_temp']}°C."
        
        elif any(word in message for word in ['humid', 'humidity']):
            humidity = analysis['humidity']
            comfort = "very humid" if humidity > 80 else "humid" if humidity > 60 else "comfortable" if humidity > 30 else "dry"
            return f"Humidity in {analysis['location']}{date_info} should be around {humidity}% - that feels {comfort}. Temperature around {analysis['current_temp']}°C with {analysis['condition']}."
        
        # Default comprehensive response
        return f"Weather in {analysis['location']}{date_info}: around {analysis['current_temp']}°C (feels like {analysis['feels_like']}°C) with {analysis['condition']}. Humidity: {analysis['humidity']}%, Wind: {analysis['wind_speed']} m/s. Ask me about clothing, activities, or travel advice for this location!"

    def get_weather_for_location_with_dates(self, location_name, start_date=None, end_date=None):
        """Fetch weather data for location with optional date filtering"""
        try:
            # Geocode the location
            location = self.geolocator.geocode(location_name, exactly_one=True)
            if not location:
                return None, f"Could not find location: {location_name}"
            
            lat, lon = location.latitude, location.longitude
            
            # Use the existing get_weather function which now supports date ranges
            weather_data = get_weather(lat, lon, start_date=start_date, end_date=end_date)
            
            # Add location information
            weather_data["location"] = {
                "name": location.address,
                "lat": lat,
                "lon": lon
            }
            
            return weather_data, None
            
        except Exception as e:
            return None, f"Error fetching weather data: {str(e)}"

    def get_clothing_advice(self, analysis):
        """Generate specific clothing advice based on weather analysis"""
        temp = analysis["current_temp"]
        condition = analysis["condition"]
        feels_like = analysis["feels_like"]
        wind_speed = analysis["wind_speed"]
        location = analysis["location"]
        
        advice = f"For {location} at {temp}°C (feels like {feels_like}°C) with {condition}: "
        
        # Base clothing by temperature
        if analysis["temp_comfort"] == "freezing":
            clothing = "heavy winter coat, thermal layers, insulated boots, warm gloves, and a winter hat"
        elif analysis["temp_comfort"] == "very_cold":
            clothing = "thick winter jacket, warm layers, winter boots, gloves, and a hat"
        elif analysis["temp_comfort"] == "cold":
            clothing = "warm coat or heavy jacket, long pants, closed shoes, and maybe gloves"
        elif analysis["temp_comfort"] == "cool":
            clothing = "light jacket or sweater, long pants, and closed shoes"
        elif analysis["temp_comfort"] == "mild":
            clothing = "light sweater or long sleeves, comfortable pants"
        elif analysis["temp_comfort"] == "comfortable":
            clothing = "t-shirt with light jacket/cardigan option, comfortable pants or shorts"
        elif analysis["temp_comfort"] == "warm":
            clothing = "light t-shirt, shorts or light pants, breathable fabrics"
        elif analysis["temp_comfort"] == "hot":
            clothing = "lightweight, breathable clothing, shorts, sandals, and sun protection"
        else:  # very_hot
            clothing = "minimal lightweight clothing, sun hat, and stay hydrated"
        
        advice += clothing
        
        # Add weather-specific modifications
        if analysis["precipitation"] == "rainy":
            advice += ". Don't forget a waterproof jacket or umbrella and waterproof shoes"
        elif analysis["precipitation"] == "snowy":
            advice += ". Add waterproof boots and extra warm layers for snow"
        elif analysis["precipitation"] == "stormy":
            advice += ". Stay indoors if possible, or wear protective rain gear"
        
        # Wind considerations
        if wind_speed > 20:
            advice += f". It's quite windy ({wind_speed} m/s), so consider a windbreaker"
        elif wind_speed > 10:
            advice += f". Moderate wind ({wind_speed} m/s), so avoid loose clothing"
        
        return advice

    def get_activity_advice(self, analysis):
        """Generate activity recommendations based on weather"""
        temp = analysis["current_temp"]
        location = analysis["location"]
        
        advice = f"For activities in {location}: "
        
        if analysis["precipitation"] == "stormy":
            return advice + "It's stormy weather - perfect for indoor activities like museums, shopping centers, cafes, or staying cozy at home."
        elif analysis["precipitation"] == "rainy":
            return advice + f"With {analysis['condition']}, consider indoor activities or outdoor activities with rain protection. Museums, shopping, or covered markets would be great."
        elif analysis["precipitation"] == "snowy":
            return advice + "Great weather for winter activities like skiing, snowboarding, or building snowmen! Or enjoy warm indoor activities."
        
        # Clear/cloudy weather activities
        if analysis["temp_comfort"] in ["very_hot", "hot"]:
            return advice + "It's quite hot - perfect for swimming, water sports, or indoor activities during peak hours. Seek shade and stay hydrated."
        elif analysis["temp_comfort"] in ["comfortable", "warm"]:
            return advice + "Excellent weather for outdoor activities like hiking, picnics, sports, cycling, or exploring the city!"
        elif analysis["temp_comfort"] in ["mild", "cool"]:
            return advice + "Good weather for outdoor activities with proper clothing - hiking, walking tours, outdoor markets, or sightseeing."
        elif analysis["temp_comfort"] in ["cold", "very_cold", "freezing"]:
            return advice + "Bundle up for outdoor activities, or enjoy indoor attractions like museums, galleries, cafes, or heated shopping centers."
        
        return advice + "Generally good conditions for most activities with appropriate clothing."

    def get_travel_advice(self, analysis):
        """Generate travel-specific advice"""
        location = analysis["location"]
        visibility = analysis["visibility"]
        wind_speed = analysis["wind_speed"]
        
        advice = f"Travel conditions in {location}: "
        
        # Visibility
        if visibility < 1:
            advice += "Poor visibility due to fog/weather - exercise caution when driving. "
        elif visibility < 5:
            advice += "Reduced visibility - drive carefully and use headlights. "
        else:
            advice += "Good visibility for travel. "
        
        # Weather conditions
        if analysis["precipitation"] == "stormy":
            advice += "Severe weather - avoid unnecessary travel, flights may be delayed."
        elif analysis["precipitation"] == "rainy":
            advice += "Wet roads - drive slowly and allow extra time for travel."
        elif analysis["precipitation"] == "snowy":
            advice += "Snow conditions - use winter tires, carry emergency supplies."
        
        # Wind
        if wind_speed > 25:
            advice += f" Very windy conditions ({wind_speed} m/s) - high vehicles should be cautious."
        elif wind_speed > 15:
            advice += f" Windy ({wind_speed} m/s) - be careful with lightweight vehicles."
        
        return advice

# Initialize the dynamic chatbot
_dynamic_chatbot = None

def ai_chat_response(user_message, city, weather_data, start_date=None, end_date=None):
    """Dynamic weather chatbot with location and date awareness"""
    global _dynamic_chatbot
    if _dynamic_chatbot is None:
        _dynamic_chatbot = DynamicWeatherChatbot()
    
    try:
        # Parse date context from the message or use provided dates
        date_context = None
        
        # If user provides specific dates, try to parse them
        if start_date:
            try:
                from datetime import datetime
                if isinstance(start_date, str):
                    # Parse date string (assuming YYYY-MM-DD format)
                    date_context = datetime.strptime(start_date, '%Y-%m-%d').date()
                else:
                    date_context = start_date
            except:
                pass
        
        # Use the dynamic chatbot with the provided city, date context, and date range
        response = _dynamic_chatbot.get_response(
            user_message, 
            location_name=city, 
            date_context=date_context,
            start_date=start_date,
            end_date=end_date
        )
        return response
    except Exception as e:
        # Fallback to simple response
        date_info = f" for {start_date} to {end_date}" if start_date and end_date else ""
        return f"Sorry, I'm having trouble processing your request. Please try asking a different question about weather in {city}{date_info}."

import numpy as np
from sklearn.linear_model import LinearRegression

def predict_next_temp(weather_data):
    """Predict next temperature using linear regression on daily forecast data"""
    daily_forecast = weather_data.get("daily", [])
    if len(daily_forecast) < 2:
        return None
    
    # Extract day temperatures from daily forecast
    temps = []
    for day in daily_forecast:
        day_temp = day.get("temp", {}).get("day")
        if day_temp is not None:
            temps.append(day_temp)
    
    if len(temps) < 2:
        return None
    
    X = np.arange(len(temps)).reshape(-1, 1)
    y = np.array(temps)
    model = LinearRegression().fit(X, y)
    pred = model.predict([[len(temps)]])[0]
    return round(pred, 2)
