# Air Conditioning Service Management - Backend API

Django REST API backend for managing air conditioning service operations with JWT authentication and role-based access control.

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

3. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

4. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/api/`

## 📋 Features

- **Custom User Model** with role-based access (ADMIN, CLIENT, TECHNICIAN)
- **JWT Authentication** with token refresh
- **CRUD Operations** for all entities
- **Role-based Permissions** and data filtering
- **SQLite Database** for easy setup
- **CORS Support** for frontend integration

## 🔧 API Endpoints

### Authentication
- `POST /api/token/` - Obtain JWT access and refresh tokens
- `POST /api/token/refresh/` - Refresh access token

### User Management
- `GET /api/users/` - List users (role-based filtering)
- `POST /api/users/` - Create user (admin only)
- `GET /api/users/{id}/` - Get user details
- `PUT/PATCH /api/users/{id}/` - Update user
- `DELETE /api/users/{id}/` - Delete user (admin only)
- `GET /api/users/me/` - Get current user profile

### Client Management
- `GET /api/clients/` - List clients
- `POST /api/clients/` - Create client
- `GET /api/clients/{id}/` - Get client details
- `PUT/PATCH /api/clients/{id}/` - Update client
- `DELETE /api/clients/{id}/` - Delete client (admin only)
- `GET /api/clients/{id}/sites/` - Get client sites

### Site Management
- `GET /api/sites/` - List sites
- `POST /api/sites/` - Create site
- `GET /api/sites/{id}/` - Get site details
- `PUT/PATCH /api/sites/{id}/` - Update site
- `DELETE /api/sites/{id}/` - Delete site (admin only)

### Technician Management
- `GET /api/technicians/` - List technicians
- `POST /api/technicians/` - Create technician (admin only)
- `GET /api/technicians/{id}/` - Get technician details
- `PUT/PATCH /api/technicians/{id}/` - Update technician
- `DELETE /api/technicians/{id}/` - Delete technician (admin only)
- `GET /api/technicians/available/` - List available technicians
- `PATCH /api/technicians/{id}/toggle_availability/` - Toggle availability

### Team Group Management
- `GET /api/team-groups/` - List team groups
- `POST /api/team-groups/` - Create team group (admin only)
- `GET /api/team-groups/{id}/` - Get team group details
- `PUT/PATCH /api/team-groups/{id}/` - Update team group (admin only)
- `DELETE /api/team-groups/{id}/` - Delete team group (admin only)
- `POST /api/team-groups/{id}/add_technician/` - Add technician to team
- `DELETE /api/team-groups/{id}/remove_technician/` - Remove technician from team

## 🔐 Authentication

### Test User Credentials
- **Username**: `testuser`
- **Password**: `testpass123`
- **Role**: `ADMIN`

### JWT Token Usage
Include the JWT token in your requests:
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     http://localhost:8000/api/users/
```

## 📊 Database Models

### User (Custom)
- Inherits from AbstractUser
- `role` field with choices: ADMIN, CLIENT, TECHNICIAN
- `phone_number` field
- Created/updated timestamps

### Client
- One-to-one relationship with User
- `company_name`, `contact_person`, `billing_address`
- `is_active` status

### Site
- Foreign key to Client
- `site_name`, `address`, `contact_person`, `contact_phone`
- `is_active` status

### Technician
- One-to-one relationship with User
- `employee_id`, `specialization`, `license_number`
- `hire_date`, `is_available` status

### TeamGroup
- Many-to-many relationship with Technician
- `name`, `description`, `team_lead`
- `is_active` status

## 🛠️ Development

### Dependencies
- Django==4.2.7
- djangorestframework==3.14.0
- django-cors-headers==4.3.1
- djangorestframework-simplejwt==5.3.0
- Pillow==10.1.0

### Configuration
- Custom user model: `core.User`
- JWT authentication configured
- CORS enabled for frontend integration
- SQLite database for development

### Admin Interface
Access the Django admin at `http://localhost:8000/admin/` with your superuser credentials.

## 🔄 Next Steps

Future enhancements could include:
- Service request management
- Work order tracking
- Equipment maintenance scheduling
- Invoice generation
- Reporting and analytics
- Email notifications
- File upload capabilities

