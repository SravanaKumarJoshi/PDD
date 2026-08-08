# Polysaccharide Selector - MVP

AI-powered material recommendation system for selecting the best natural polysaccharide for biomedical packaging applications.

## 🎯 Overview

This Streamlit application helps biomedical engineers and researchers select optimal polysaccharides by:
- Matching user requirements with material properties
- Using machine learning to predict suitability
- Providing visual comparisons and detailed explanations
- Offering a transparent, data-driven decision process

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd d:\Sravan\PDD
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - Windows (PowerShell):
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - Windows (Command Prompt):
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

## 📁 Project Structure

```
d:/Sravan/PDD/
├── app.py                          # Main Streamlit entry point
├── pages/
│   ├── 1_Recommend.py              # Material recommendation page
│   ├── 2_Dataset_Browser.py       # Dataset browser & filters
│   └── 3_Model_Training.py        # Model training & evaluation
├── src/
│   ├── __init__.py                 # Package initialization
│   ├── data.py                     # Data loading & validation
│   ├── model.py                    # ML training & prediction
│   ├── scoring.py                  # Recommendation logic
│   └── viz.py                      # Plotly visualizations
├── data/
│   └── polymers.csv                # Polymer properties dataset
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## 🔬 How It Works

### Recommendation Algorithm

The system uses a **hybrid scoring approach** combining similarity matching and machine learning:

#### 1. Hard Filters (Must Pass)
- **Biocompatibility**: Polymer must meet minimum biocompatibility score
- **Sterilization**: Polymer must support all selected sterilization methods (gamma, EtO, steam)

#### 2. Similarity Score (60% weight)
Measures how close polymer properties match user targets:
- Normalizes all numeric features using dataset min/max
- Computes normalized distance for: tensile strength, flexibility, WVTR, oxygen permeability
- Special range-based scoring for biodegradation days (full score within range, exponential decay outside)
- Converts to 0-100 scale

#### 3. ML Suitability Score (40% weight)
- RandomForest classifier predicts suitability probability (0-1)
- Trained on `suitability_label` column (historical data)
- Uses 11 features: mechanical, barrier, biological, and sterilization properties
- Scaled to 0-100 for final score calculation

#### 4. Penalty Application
- **Antimicrobial requirement**: If user requires antimicrobial properties but polymer lacks them:
  - Apply 30% penalty (multiply by 0.7)
  - Flag result with "⚠️ Requires antimicrobial additive/coating"

#### 5. Final Score Calculation
```
final_score = (0.6 × similarity + 0.4 × ML_suitability) × penalty
```

Polymers are ranked by final score in descending order.

### User Workflow

1. **Train Model** (Model Training page)
   - Configure train/test split and random seed
   - Train RandomForest classifier
   - View accuracy, precision, recall, F1, confusion matrix
   - Model is cached in session state

2. **Set Requirements** (Recommend page)
   - Select application type
   - Specify target properties (tensile strength, flexibility, WVTR, O₂ permeability)
   - Set biodegradation range
   - Choose biocompatibility minimum
   - Toggle antimicrobial requirement
   - Select sterilization methods

3. **Get Recommendations**
   - View top 5 ranked polymers with match percentages
   - See "Best Overall" with detailed explanation
   - Compare properties visually (radar chart, bar chart, score breakdown)
   - Review flags for any unmet requirements

4. **Browse Dataset** (Dataset Browser page)
   - Filter and explore all polymers
   - View statistics and distributions
   - Download filtered data as CSV

## 📊 Dataset

### Current Polymers

The dataset includes 10 natural polysaccharides:
- Chitosan
- Alginate
- Cellulose
- Nanocellulose
- Starch
- Pectin
- Dextran
- Hyaluronic Acid
- Carrageenan
- Gellan Gum

### Schema

| Column | Type | Description |
|--------|------|-------------|
| polymer | string | Polymer name |
| tensile_strength | float | Tensile strength (MPa) |
| flexibility | float | Flexibility score (1-10) |
| wvtr | float | Water vapor transmission rate (g/m²/day) |
| oxygen_permeability | float | Oxygen permeability coefficient |
| biocompatibility | int | Biocompatibility score (1-10) |
| antimicrobial | binary | Has antimicrobial properties (0/1) |
| biodegradation_days | int | Days to complete degradation |
| solubility | string | Solubility level (low/medium/high) |
| film_forming | binary | Can form continuous films (0/1) |
| sterilization_gamma | binary | Tolerates gamma radiation (0/1) |
| sterilization_eto | binary | Tolerates ethylene oxide (0/1) |
| sterilization_steam | binary | Tolerates steam/autoclave (0/1) |
| suitability_label | binary | ML training label - suitable (0/1) |

### Extending the Dataset

To add more polymers:

1. Open `data/polymers.csv` in a spreadsheet editor or text editor
2. Add new rows with all required columns
3. Ensure numeric values are properly formatted (no commas, use decimal points)
4. Binary columns should be 0 or 1
5. Solubility should be "low", "medium", or "high"
6. Save and restart the application

**Important:** All 14 columns are required. Missing values will cause validation errors.

## 🛠️ Technical Details

### Dependencies

- **streamlit**: Web framework for interactive UI
- **pandas**: Data manipulation and analysis
- **scikit-learn**: Machine learning (RandomForest)
- **plotly**: Interactive visualizations
- **numpy**: Numerical operations

### ML Model

**RandomForestClassifier Configuration:**
- `n_estimators=100`: 100 decision trees
- `max_depth=5`: Limits tree depth to prevent overfitting
- `class_weight='balanced'`: Handles imbalanced classes
- `random_state`: Configurable for reproducibility

**Features (11):**
All numeric/binary properties except polymer name and solubility

**Target:**
`suitability_label` (binary classification)

### Storage

- **MVP uses CSV only** (no database)
- Dataset loaded and cached in session state
- Model trained in-session (not persisted to disk)
- Suitable for datasets up to ~1000 polymers

## 🧪 Testing the Application

### Basic Functionality Test

1. Start the application
2. Navigate to **Model Training** page
3. Click "Train Model" and verify metrics appear
4. Go to **Recommend** page
5. Enter test requirements:
   - Application: "Wound dressing packaging"
   - Tensile: 80 MPa
   - Flexibility: 7
   - WVTR: 450
   - O₂ Perm: 12
   - Biocompat: 8
   - Antimicrobial: ON
   - Biodeg: 60-120 days
   - Sterilization: Gamma + EtO
6. Click "Find Recommendations"
7. Verify you get top 5 results with charts
8. Navigate to **Dataset Browser**
9. Apply filters and download CSV

## 🔧 Troubleshooting

### Application won't start
- Ensure Python 3.11+ is installed: `python --version`
- Verify virtual environment is activated (you should see `(venv)` in prompt)
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

### "Dataset not loaded" error
- Verify `data/polymers.csv` exists
- Check CSV has all 14 required columns
- Ensure no empty cells in the CSV

### "Model not trained" error
- Go to Model Training page first
- Click "Train Model" button
- Model must be trained in each session (not persisted)

### Poor visualization rendering
- Update browser to latest version
- Try a different browser (Chrome/Edge recommended)
- Check console for JavaScript errors

### Low model accuracy
- Dataset is small (10 polymers), expect moderate metrics
- Increase dataset size for better ML performance
- Adjust test/train split

## 🚀 Future Enhancements

Potential improvements beyond MVP:

- **Database Integration**: Move to SQLite/PostgreSQL for scalability
- **Persistent Model**: Save trained models to disk
- **User Authentication**: Multi-user support with saved preferences
- **Advanced Filtering**: Cost, availability, supplier information
- **Batch Recommendations**: Upload multiple requirements at once
- **Export Reports**: PDF generation with recommendations
- **API Endpoint**: REST API for programmatic access
- **Literature References**: Link to papers for each polymer
- **Sensitivity Analysis**: Show how score changes with property variations

## 📝 Notes

- This is an MVP focused on core functionality
- Sample dataset values are realistic but simplified
- For production use, validate against experimental data
- Model retrains each session (not persisted between runs)
- No authentication or multi-user support in MVP

## 📄 License

This project is for educational and research purposes.

## 🤝 Contributing

To extend this application:

1. Add new polymers to `data/polymers.csv`
2. Modify scoring logic in `src/scoring.py`
3. Add new visualizations in `src/viz.py`
4. Create additional pages in `pages/` folder
5. Update model configuration in `src/model.py`

---

**Built with ❤️ using Streamlit, scikit-learn, and Plotly**
