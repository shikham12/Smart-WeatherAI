#  SmartWeatherAI — Agentic AI Weather Assistant

> An intelligent, agentic AI-powered weather assistant that not only reports conditions — it analyzes, predicts, and advises like a human expert.

---

##  Overview

SmartWeatherAI is a full-stack Flask web application that integrates real-time weather data, machine learning, and generative AI to provide intelligent, context-aware weather insights.
It combines data perception, reasoning, and autonomous action — the hallmarks of agentic AI.

Users can query weather by city, ZIP, landmark, or GPS coordinates, view current and 5-day forecasts, interact with a conversational AI assistant, and receive human-like summaries and recommendations such as clothing tips, activity suggestions, or travel advisories.

---

##  Tech Stack

| Layer         | Component             | Purpose                   | Technology                           |
| --------------| --------------------- | ------------------------- | ------------------------------------ |
| Database      | `WeatherRequest`      | Persistent storage (CRUD) | SQLAlchemy ORM + SQLite              |
| AI Summary    | `BART-Large-CNN`      | Text summarization        | Hugging Face Transformers            |
| ML Prediction | Linear Regression     | Temperature forecasting   | Scikit-learn                         |
| Geocoding     | Nominatim             | Location resolution       | Geopy                                |
| Weather Data  | OpenWeatherMap        | Real-time weather API     | REST API                             |
| Chatbot       | DynamicWeatherChatbot | Conversational AI         | Custom Python / Optional GPT         |
| Backend       | Flask + SQLAlchemy    | Web and API backend       | Flask ecosystem                      |
| Frontend      | Bootstrap 5.3.0       | Responsive UI             | HTML5 / CSS3 / JS / Plotly / Leaflet |

---

##  Key Features

* Real-Time Weather Retrieval — Current and 5-day forecast via OpenWeatherMap API
* Intelligent Geocoding — City, ZIP, coordinates, or landmark detection (Geopy)
* AI Weather Summaries — Transformer-based natural-language summarization (BART)
* Conversational Assistant — Chatbot with context-aware responses and recommendations
* Predictive Analytics — ML model predicts next-day temperature trends
* Data Persistence — SQLite CRUD operations and data export (CSV / JSON / Markdown)
* Interactive Visualization — Plotly charts and Leaflet maps for insights
* Agentic AI Behavior — Perceives (input/API), reasons (AI + ML), acts (autonomous response)
* Deployment Ready — Dockerized with environment variable support for API keys

---

##  Agentic AI Capabilities

| Trait      | Implementation                                                     |
| -----------| ------------------------------------------------------------------ |
| Perception | User input + API sensing (OpenWeatherMap, Geopy)                   |
| Reasoning  | AI text summarization and ML forecasting                           |
| Action     | Autonomous chatbot responses, visualization, data storage          |
| Adaptation | Remembers past queries; customizable for learning user preferences |

---

##  AI & ML Components

* Transformer Model: [BART-Large-CNN](https://huggingface.co/facebook/bart-large-cnn) for summarizing forecasts into readable text.
* Machine Learning: Linear Regression (Scikit-learn) for temperature forecasting.
* Chatbot Engine: Custom NLP rules + optional OpenAI GPT integration for enhanced reasoning.

---

##  Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/SmartWeatherAI.git
cd SmartWeatherAI

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API keys
Create a .env file with:
OPENWEATHER_API_KEY=<your_key>

# 5. Run the app
flask run
```

Then visit: `http://localhost:5000`

---

##  Example Features

* Enter a city or ZIP → Get current weather and 5-day forecast
* Ask chatbot: *“Should I carry an umbrella tomorrow in Mumbai?”*
* Export data as `.csv` or `.json`
* View AI-generated weather summaries
* See temperature trends on interactive Plotly charts
* Explore location via interactive Leaflet map

---

##  Future Enhancements

*  Voice input/output (speech-to-text)
*  Smart travel planner (multi-agent reasoning)
*  Redis caching for faster performance
*  Severe weather alerts

---

##  License

This project is open-source under the [MIT License](LICENSE).

---
