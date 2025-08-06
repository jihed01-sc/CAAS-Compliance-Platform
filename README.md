# Compliance as a Service (CAAS) Application

## 📋 Project Overview

The Compliance as a Service (CAAS) Application is a comprehensive Django-based platform designed to streamline organizational compliance management. It provides tools for managing compliance frameworks (ISO 27001, SOC 2, NIS2, etc.), tracking control implementations, managing evidence, and conducting compliance assessments through an integrated questionnaire system.

### Key Features

- **Multi-Framework Support**: Support for major compliance frameworks including ISO 27001, SOC 2, NIS2, and IEC standards
- **Control Management**: Assign, track, and manage compliance controls across information systems
- **Evidence Management**: Upload, review, and approve compliance evidence
- **Smart Questionnaire System**: External ngrok-deployed questionnaire for compliance assessments
- **Dashboard Analytics**: Real-time compliance status tracking and progress monitoring
- **Notification System**: Automated alerts for deadlines, assignments, and status changes
- **Role-based Access**: Support for different user roles (owners, controllers, reviewers)

## 🚀 Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Redis server (for Celery background tasks)
- SQLite (default) or PostgreSQL/MySQL for production
- **Required Excel Files**: `TheMappin_Matrix.xlsx` and `Unified_Framework.xlsx` (located in `docs/` folder)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd CAAS_App
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r compliance/requirements.txt
```

**Required Dependencies:**
- Django==4.2.7
- djangorestframework==3.14.0
- django-cors-headers==4.3.1
- django-filter==23.3
- python-decouple==3.8
- celery==5.3.4
- redis==5.0.1
- django-celery-beat==2.5.0
- openpyxl==3.1.2

### Step 4: Environment Configuration

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
```

### Step 5: Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### Step 6: Load Initial Data (Optional)

```bash
# Create test data for development
python create_test_data.py

# Create test questionnaire results
python create_test_questionnaire_result.py
```

### Step 6.1: Import Framework Data (Required)

The CAAS application requires two essential Excel files for proper framework and control mapping functionality:

#### Required Files:
1. **`TheMappin_Matrix.xlsx`** - Contains control mappings between different compliance frameworks
2. **`Unified_Framework.xlsx`** - Contains the unified framework structure and control definitions

#### Upload Process:

1. **Locate the Excel Files**:
   ```
   docs/
   ├── TheMappin_Matrix.xlsx
   └── Unified_Framework.xlsx
   ```

2. **Import Framework Data**:
   ```bash
   # Import the unified framework data
   python import_excel_data.py
   ```

3. **Verify Data Import**:
   - Access the Django admin panel: `http://localhost:8000/admin/`
   - Navigate to `Compliance > Frameworks` to verify frameworks are loaded
   - Check `Compliance > Controls` to verify control definitions are imported
   - Verify `Compliance > Control Mappings` to ensure cross-framework mappings are established

#### What These Files Contain:

**TheMappin_Matrix.xlsx**:
- Cross-framework control mappings (ISO 27001 ↔ SOC 2 ↔ NIS2 ↔ IEC)
- Control equivalencies and relationships
- Gap analysis data for framework transitions
- Compliance correlation matrices

**Unified_Framework.xlsx**:
- Complete control catalog across all supported frameworks
- Control descriptions, implementation guidance, and evidence requirements
- Control categories and subcategories
- Risk levels and priority classifications
- Assessment criteria and testing procedures

#### Alternative Manual Upload (if import script fails):

1. **Access Django Admin**: `http://localhost:8000/admin/`
2. **Navigate to Frameworks Section**
3. **Upload via Admin Interface**:
   - Go to `Compliance > Frameworks`
   - Use the "Import" functionality (if available)
   - Or manually create framework entries based on Excel data

#### Troubleshooting Framework Import:

**Issue**: "Excel file not found"
- **Solution**: Ensure files are in the `docs/` directory with exact names:
  - `TheMappin_Matrix.xlsx` (note the space in the filename)
  - `Unified_Framework.xlsx`

**Issue**: "Import script errors"
- **Solution**: Check that openpyxl is installed: `pip install openpyxl==3.1.2`

**Issue**: "Duplicate framework entries"
- **Solution**: Clear existing data before re-import:
  ```bash
  python manage.py shell
  >>> from compliance.models import Framework, Control
  >>> Framework.objects.all().delete()
  >>> Control.objects.all().delete()
  >>> exit()
  ```

### Step 7: Start Redis Server

```bash
# Windows (if Redis is installed)
redis-server

# macOS with Homebrew
brew services start redis

# Linux
sudo systemctl start redis
```

### Step 8: Start Celery Worker (Optional - for background tasks)

```bash
# In a separate terminal
celery -A compliance_project worker --loglevel=info
```

### Step 9: Run the Development Server

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## 🔧 Usage Guide

### Basic Application Usage

1. **Login/Register**: Access the application at `http://localhost:8000`
2. **Create Information Systems**: Define the systems you want to manage compliance for
3. **Assign Frameworks**: Choose relevant compliance frameworks (ISO 27001, SOC 2, etc.)
4. **Assign Controls**: Map specific controls to your systems
5. **Upload Evidence**: Provide documentation supporting control implementations
6. **Track Progress**: Monitor compliance status through the dashboard

### 📋 Questionnaire Function Setup & Deployment

The CAAS application includes an advanced questionnaire system that runs on an external platform via ngrok tunneling. This feature provides comprehensive compliance assessments and generates detailed reports.

#### Prerequisites for Questionnaire Function

1. **Google Colab Account**: Access to run the questionnaire notebook
2. **ngrok Account**: For creating secure tunnels (free tier available)
3. **Active Internet Connection**: Required for external deployment

#### Step-by-Step Questionnaire Deployment

##### Step 1: Deploy Questionnaire via Google Colab

1. **Access the Colab Notebook**:
   - Open your browser and navigate to Google Colab
   - Upload or access the questionnaire deployment notebook
   - The notebook contains the questionnaire logic and ngrok integration

2. **Run the Colab Notebook**:
   ```python
   # In the Colab notebook, execute all cells
   # The notebook will automatically:
   # - Install required dependencies
   # - Set up the questionnaire server
   # - Generate an ngrok tunnel
   ```

3. **Obtain the ngrok URL**:
   - After running the notebook, you'll see output similar to:
   ```
   Public URL: https://abc123def456.ngrok-free.app
   ```
   - **Copy this URL** - you'll need it for the next step

##### Step 2: Configure the ngrok URL in CAAS Application

1. **Locate the questionnaire method**:
   - Navigate to: `compliance/views.py`
   - Find the `questionnaire_view` function (around line 2247)

2. **Replace the ngrok URL**:
   ```python
   @login_required
   def questionnaire_view(request):
       """Redirect to ngrok questionnaire link with user tracking"""
       # Store user session info before redirect
       request.session['questionnaire_start_time'] = timezone.now().isoformat()
       request.session['questionnaire_user_id'] = request.user.id

       # Mark questionnaire as started for all user systems
       user_systems = InformationSystem.objects.filter(owner=request.user)
       for system in user_systems:
           request.session[f'questionnaire_started_{system.id}'] = True

       # 🔄 REPLACE THIS URL WITH YOUR NEW NGROK URL 🔄
       return redirect('https://YOUR-NEW-NGROK-URL-HERE.ngrok-free.app')
   ```

3. **Update the URL**:
   - Replace `https://85e5f0c29084.ngrok-free.app` with your new ngrok URL
   - Example: `https://abc123def456.ngrok-free.app`

##### Step 3: Update Additional ngrok References (if applicable)

Check and update these files if they contain hardcoded ngrok URLs:

1. **`compliance/views_fixed.py`** (around line 696):
   ```python
   ngrok_url = "https://YOUR-NEW-NGROK-URL-HERE.ngrok-free.app"
   ```

2. **Any deployment scripts or configuration files**

##### Step 4: Restart the Application

```bash
# Stop the current server (Ctrl+C)
# Restart the development server
python manage.py runserver
```

#### How the Questionnaire Works

1. **User Access**: Users click "Start Questionnaire" in the CAAS dashboard
2. **Redirect**: Application redirects to the ngrok-deployed questionnaire
3. **Assessment**: Users complete the comprehensive compliance questionnaire
4. **Results**: Questionnaire generates:
   - Overall compliance score (0-100%)
   - Maturity level assessment
   - Risk level evaluation
   - Framework recommendations
   - Gap analysis
   - Priority actions

5. **Integration**: Results are stored in the `QuestionnaireResult` model and displayed in the dashboard

## 🛠️ Key Features

### Compliance Management
- **Framework Support**: ISO 27001, SOC 2, NIS2, IEC standards
- **Control Tracking**: Assign and monitor control implementations
- **Evidence Management**: Upload, review, and approve compliance evidence
- **Progress Monitoring**: Real-time compliance status tracking

### Smart Assessment System
- **External Questionnaire**: ngrok-deployed assessment tool
- **Comprehensive Analysis**: Multi-dimensional compliance evaluation
- **Automated Recommendations**: Framework suggestions based on assessment
- **Gap Analysis**: Identify compliance gaps and priority actions

### User Management
- **Role-based Access**: Owners, controllers, reviewers
- **Profile Management**: Controller profiles with expertise areas
- **Notification System**: Automated alerts and reminders

### Reporting & Analytics
- **Dashboard Views**: Real-time compliance metrics
- **Progress Tracking**: System-level and control-level progress
- **Deadline Management**: Track and alert on upcoming deadlines
- **Evidence Tracking**: Monitor evidence upload and approval status

## 🔍 Troubleshooting

### Common Issues and Solutions

#### Questionnaire Issues

**Issue**: "Questionnaire link not working"
- **Cause**: ngrok URL expired or incorrect
- **Solution**: 
  1. Re-run the Colab notebook to generate a new ngrok URL
  2. Update the URL in `compliance/views.py` line ~2258
  3. Restart the Django server

**Issue**: "Cannot access questionnaire from CAAS application"
- **Cause**: CSRF protection blocking external redirect
- **Solution**: Check that your ngrok domain is added to `CSRF_TRUSTED_ORIGINS` in `settings.py`

**Issue**: "Questionnaire results not appearing in dashboard"
- **Cause**: Integration callback not configured properly
- **Solution**: Ensure the questionnaire callback endpoint is correctly configured

#### Application Issues

**Issue**: "Static files not loading"
- **Solution**: 
  ```bash
  python manage.py collectstatic
  ```

**Issue**: "Database migrations failing"
- **Solution**:
  ```bash
  python manage.py makemigrations --merge
  python manage.py migrate
  ```

**Issue**: "Redis connection error"
- **Solution**: 
  1. Ensure Redis server is running
  2. Check Redis configuration in settings
  3. Verify Redis URL in environment variables

**Issue**: "Permission denied errors"
- **Solution**: Check user permissions and ensure proper role assignments

#### ngrok-Specific Issues

**Issue**: "ngrok tunnel disconnected"
- **Cause**: Free ngrok tunnels have time limits
- **Solution**: 
  1. Re-run the Colab notebook
  2. Update the URL in the application
  3. Consider upgrading to ngrok Pro for persistent tunnels

**Issue**: "ngrok URL returns 404"
- **Cause**: Questionnaire service not running
- **Solution**: 
  1. Check that all Colab notebook cells executed successfully
  2. Verify the questionnaire server is running
  3. Check for any errors in the Colab output

### Development Tips

1. **Environment Variables**: Use `.env` file for sensitive configuration
2. **Debug Mode**: Set `DEBUG=True` for development, `False` for production
3. **Database Backups**: Regularly backup your database, especially before migrations
4. **Log Monitoring**: Check Django logs for detailed error information

## 🤝 Contributing & Support

### Contributing Guidelines

1. **Fork the Repository**: Create a personal fork of the project
2. **Create Feature Branch**: `git checkout -b feature/your-feature-name`
3. **Follow Code Standards**: 
   - Use Django best practices
   - Write clear, commented code
   - Include docstrings for functions and classes
4. **Test Your Changes**: Ensure all functionality works as expected
5. **Submit Pull Request**: Include detailed description of changes

### Code Style Guidelines

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Comment complex logic
- Write docstrings for all public methods
- Use Django's built-in features and conventions

### Reporting Issues

When reporting issues, please include:

1. **Environment Details**: OS, Python version, Django version
2. **Error Messages**: Complete error logs and stack traces
3. **Steps to Reproduce**: Detailed steps to recreate the issue
4. **Expected Behavior**: What should happen vs. what actually happens
5. **Screenshots**: If applicable, include screenshots of errors

### Getting Help

- **Documentation**: Check this README and inline code documentation
- **Django Documentation**: [docs.djangoproject.com](https://docs.djangoproject.com/)
- **Community Forums**: Django community forums and Stack Overflow
- **Issue Tracker**: Use the repository's issue tracker for bug reports

## 📄 License & Acknowledgments

### License

This project is licensed under the MIT License - see the LICENSE file for details.

### Acknowledgments

- **Django Community**: For the excellent web framework
- **ngrok**: For secure tunnel services enabling external questionnaire deployment
- **Google Colab**: For providing the platform for questionnaire deployment
- **Redis**: For reliable background task processing
- **Bootstrap**: For responsive UI components

### Third-Party Libraries

- Django REST Framework for API development
- Celery for background task processing
- Redis for caching and message brokering
- OpenPyXL for Excel file processing
- CORS Headers for cross-origin request handling

---

## 📞 Support

For technical support or questions about this application:

1. **Check Documentation**: Review this README and inline documentation
2. **Search Issues**: Look through existing issues in the repository
3. **Create New Issue**: If your problem isn't addressed, create a new issue with detailed information
4. **Community Resources**: Leverage Django and Python community resources

---

**Happy Compliance Management! 🛡️**

*Remember to keep your ngrok URLs updated and monitor your questionnaire deployments for optimal user experience.*
