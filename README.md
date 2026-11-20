# Style-AI ✨

### Profile-Based Personalized Fashion Styling System

Style-AI provides outfit, color palette, hairstyle, jewelry, and accessory suggestions based on profile selections such as body type, skin tone, face shape, occasion, and fashion preferences.

The current Flask recommendation API uses deterministic, profile-based rules. It does not load or claim predictions from a trained machine-learning model.

---

## 🚀 Features

### Personalized Fashion Recommendations

* Outfit Recommendations
* Color Palette Suggestions
* Hairstyle Recommendations
* Jewelry Recommendations
* Accessory Suggestions

### User Profile Analysis

* Height & Weight Analysis
* Body Type Selection
* Skin Tone Selection
* Face Shape Selection
* Occasion Selection
* Fashion Style Preferences

### Recommendation Categories

* Casual Wear
* College Wear
* Office Wear
* Party Wear
* Wedding Wear
* Traditional Wear
* Indo-Western Wear

---

## 🧩 Current Recommendation Logic

Recommendations are selected from curated styling rules using the following profile inputs:

* Body Type
* Skin Tone
* Face Shape
* Occasion
* Preferred Fashion Style
* Hair length and texture

---

## 🛠️ Technology Stack

### Frontend

* HTML5
* CSS3
* JavaScript

### Backend

* Flask

### Database

* Not currently connected to the Flask recommendation workflow

### Image Analysis

* Python
* OpenCV
* Pillow

### Development Tools

* VS Code
* Git
* GitHub

## ▶️ Run the application locally

The Flask server serves both the frontend and API. From the repository root in PowerShell:

```powershell
py -3.11 -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python backend\app.py
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Do not open `frontend/index.html` directly or use a separate static server; the frontend calls the Flask API at the same origin.

If port 8000 is already in use, set a free port before starting Flask:

```powershell
$env:PORT = "8001"
python backend\app.py
```

Then open [http://127.0.0.1:8001/](http://127.0.0.1:8001/).

Run backend tests with:

```powershell
python -m pytest -q backend\test_app.py
```

### Current backend scope

- `GET /api/health` checks that the Flask server is responding.
- `POST /api/recommend` validates the profile and returns deterministic, rule-based styling suggestions. These are not trained machine-learning predictions.
- `POST /api/upload` validates and stores JPG, PNG, and WEBP images, then uses OpenCV for face detection and skin-tone estimation when one face is found. Face shape remains a manual selection.
- `GET /api/uploads/<filename>` serves a previously uploaded image.

Images are limited to 10 MB and stored under `backend/uploads/`. The current styling suggestions do not require MongoDB or model files.

---

## 📸 Screenshots

### User Profile Page and Outputs

## Project Demo

<h2>📸 Screenshots</h2>

<h3>1. User Profile Input</h3>
<img src="frontend/assets/images/style_user.jpg" width="800">

<h3>2. User Data Analysis</h3>
<img src="frontend/assets/images/user_data.jpg" width="800">

<h3>3. Fashion Recommendations Output</h3>
<img src="frontend/assets/images/user_output1.jpg" width="800">

<h3>4. Styling Suggestions & Results</h3>
<img src="frontend/assets/images/user_output2.png" width="800">

> Screenshots will be updated as new modules are completed.

---

## 🚧 Development Status

Style-AI is in development. Its current recommendations are deterministic styling rules, not trained machine-learning output.

### Completed Modules

✅ Profile form with manual body, skin-tone, and face-shape selection

✅ Flask server for the frontend and API

✅ Profile validation and rule-based styling recommendation API

✅ Image upload validation, OpenCV preprocessing, face detection, and basic skin-tone estimation

### In Progress

🔄 Improving skin-tone reliability; results may be unknown and require manual selection

### Upcoming Features

📌 Face Shape Detection from Images

📌 AI-Powered Image Upload Analysis

📌 Virtual Fashion Try-On

📌 Deep Learning-Based Recommendations

📌 Fashion Trend Prediction

---

## 🎯 Project Objectives

* Provide personalized fashion recommendations from user-selected profile information.
* Improve styling decisions through data-driven suggestions.
* Recommend outfits based on body type and occasion.
* Suggest colors suitable for different skin tones.
* Recommend hairstyles according to face shape.
* Provide matching jewelry and accessory recommendations.
* Build an intelligent fashion assistant for women.

---

## 📈 Future Enhancements

* Computer Vision Integration using OpenCV
* Facial Feature Detection
* Automated User Attribute Extraction
* Deep Learning Recommendation Models
* Mobile Application Development
* Fashion E-Commerce Integration
* Personalized Shopping Assistant

---

## 👨‍💻 Developer

**Heer Sagaria**

B.Tech Computer Science & Engineering

Machine Learning & Data Analytics Enthusiast

---

## ⭐ Project Category

**Machine Learning | Recommendation System | Data Analytics | Full-Stack Development**
