# 🐷 Pig Farm Management System

A comprehensive web-based management system for pig farms built with Flask.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

- 🔐 **User Authentication** - Secure login with admin/user roles
- 🐖 **Pig Management** - Add, view, and track individual pigs
- ⚖️ **Weight Tracking** - Record weights over time with visual charts
- 📊 **Data Visualization** - Interactive charts showing weight progression
- 📥 **CSV Export** - Export all data for analysis
- 👥 **User Management** - Admin can add/remove users
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
```bash
   git clone https://github.com/yourusername/pig-farm-manager.git
   cd pig-farm-manager
```

2. **Create virtual environment**
```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Mac/Linux
   source venv/bin/activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and change the values
   nano .env
```

5. **Run the application**
```bash
   python app.py
```

6. **Access the application**
   - Open browser: http://127.0.0.1:5000
   - Default login: `admin` / `admin123`
   - **⚠️ Change the default password immediately!**

## 📁 Project Structure
```
pig_farm_project/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── add_pig.html
│   ├── pig_detail.html
│   └── manage_users.html
├── static/               # Static files
│   ├── css/
│   │   └── main.css
│   └── js/
│       ├── main.js
│       ├── dashboard.js
│       ├── forms.js
│       └── pig-detail.js
└── instance/             # Database (not in git)
    └── pigfarm.db
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URI=sqlite:///pigfarm.db
FLASK_DEBUG=False
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
```

### Generate Secret Key
```python
import secrets
print(secrets.token_hex(32))
```

## 📖 Usage

### Admin Features
- Create and manage user accounts
- Access all system features
- Export data to CSV

### User Features
- Add new pigs
- Record weight measurements
- View weight progression charts
- Mark pigs as slaughtered

## 🛠️ Technologies Used

- **Backend**: Flask, SQLAlchemy
- **Frontend**: Bootstrap 5, JavaScript
- **Database**: SQLite
- **Charts**: Matplotlib
- **Authentication**: Werkzeug Security

## 🔒 Security Notes

- Never commit `.env` file to Git
- Change default admin password immediately
- Use strong passwords for production
- Set `FLASK_DEBUG=False` in production
- Use HTTPS in production

## 📊 Database Schema

### Users Table
- `id` (Primary Key)
- `username` (Unique)
- `password` (Hashed)
- `is_admin` (Boolean)

### Pigs Table
- `id` (Primary Key, Manual Entry)
- `name` (Optional)
- `dob` (Date of Birth)
- `sex` (Male/Female)
- `breed` (Pig Breed)
- `kill_date` (Optional)
- `status` (ALIVE/SLAUGHTERED)

### Weights Table
- `id` (Primary Key, Auto-increment)
- `pig_id` (Foreign Key)
- `weight` (Float)
- `date` (Date)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## 👨‍💻 Author

Your Name - [GitHub Profile](https://github.com/yourusername)

## 🙏 Acknowledgments

- Flask documentation
- Bootstrap framework
- Matplotlib library

## 📞 Support

For issues or questions, please open an issue on GitHub.
```
