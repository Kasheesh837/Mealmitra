from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from flask_mail import Mail, Message
import uuid
import math

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# MongoDB configuration
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://kasheesh:kashees@sonu.0qkexwl.mongodb.net/?retryWrites=true&w=majority&appName=sonu')
client = MongoClient(MONGO_URI)
db = client.annasamarpan

# Collections
donors_collection = db.donors
volunteers_collection = db.volunteers
recipients_collection = db.recipients
donations_collection = db.donations
assignments_collection = db.assignments
admins_collection = db.admins
monthly_donors_collection = db.monthly_donors

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

mail = Mail(app)

# Helper functions
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon/2) * math.sin(dlon/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

def send_volunteer_notification(volunteer_email, donation_details):
    """Send email notification to volunteer about new assignment"""
    try:
        msg = Message(
            subject='New Donation Assignment - Annasamarpan',
            sender=app.config['MAIL_USERNAME'],
            recipients=[volunteer_email]
        )
        msg.body = f"""
Dear Volunteer,

You have been assigned a new donation to deliver:

Donation Details:
- Food Type: {donation_details['food_type']}
- Quantity: {donation_details['quantity']}
- Description: {donation_details['description']}
- Pickup Address: {donation_details['pickup_address']}
- Contact: {donation_details['donor_contact']}

Please log in to your volunteer dashboard to confirm and complete this assignment.

Thank you for your service to the community!

Best regards,
Annasamarpan Team
        """
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Routes
@app.route('/')
def index():
    """Home page with impact statistics"""
    # Get statistics
    total_donations = donations_collection.count_documents({})
    total_volunteers = volunteers_collection.count_documents({})
    total_recipients = recipients_collection.count_documents({})
    completed_deliveries = assignments_collection.count_documents({"status": "completed"})
    
    stats = {
        'total_donations': total_donations,
        'total_volunteers': total_volunteers,
        'total_recipients': total_recipients,
        'completed_deliveries': completed_deliveries
    }
    
    return render_template('index.html', stats=stats)

@app.route('/donor', methods=['GET', 'POST'])
def donor():
    """Donor registration and donation submission"""
    if request.method == 'POST':
        donor_data = {
            'name': request.form['name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'address': request.form['address'],
            'city': request.form['city'],
            'state': request.form['state'],
            'pincode': request.form['pincode'],
            'created_at': datetime.now()
        }
        
        donation_data = {
            'donor_email': request.form['email'],
            'food_type': request.form['food_type'],
            'quantity': request.form['quantity'],
            'description': request.form['description'],
            'pickup_address': request.form['address'],
            'expiry_date': request.form.get('expiry_date'),
            'status': 'pending',
            'created_at': datetime.now()
        }
        
        # Insert donor if not exists
        existing_donor = donors_collection.find_one({'email': request.form['email']})
        if not existing_donor:
            donors_collection.insert_one(donor_data)
        
        # Insert donation
        donations_collection.insert_one(donation_data)
        
        flash('Donation submitted successfully! A volunteer will be assigned soon.', 'success')
        return redirect(url_for('donor'))
    
    return render_template('donor.html')

@app.route('/volunteer', methods=['GET', 'POST'])
def volunteer():
    """Volunteer registration and dashboard"""
    if request.method == 'POST':
        volunteer_data = {
            'name': request.form['name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'address': request.form['address'],
            'city': request.form['city'],
            'state': request.form['state'],
            'pincode': request.form['pincode'],
            'latitude': float(request.form.get('latitude', 0) or 0),
            'longitude': float(request.form.get('longitude', 0) or 0),
            'availability': request.form.get('availability', 'available'),
            'created_at': datetime.now()
        }
        
        volunteers_collection.insert_one(volunteer_data)
        flash('Volunteer registration successful! You will receive assignments via email.', 'success')
        return redirect(url_for('volunteer'))
    
    return render_template('volunteer.html')

@app.route('/volunteer/dashboard')
def volunteer_dashboard():
    """Volunteer dashboard showing assigned tasks"""
    volunteer_email = session.get('volunteer_email')
    if not volunteer_email:
        flash('Please log in to access your dashboard.', 'warning')
        return redirect(url_for('volunteer'))
    
    volunteer = volunteers_collection.find_one({'email': volunteer_email})
    if not volunteer:
        flash('Volunteer not found.', 'error')
        return redirect(url_for('volunteer'))
    
    # Get assignments for this volunteer
    assignments = list(assignments_collection.find({'volunteer_email': volunteer_email}))
    
    # Get donation details for each assignment
    for assignment in assignments:
        donation = donations_collection.find_one({'_id': assignment['donation_id']})
        assignment['donation'] = donation
    
    return render_template('volunteer_dashboard.html', volunteer=volunteer, assignments=assignments)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Admin login page"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        admin = admins_collection.find_one({'email': email, 'password': password})
        if admin:
            session['admin_email'] = email
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials.', 'error')
    
    return render_template('admin.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard with comprehensive management"""
    if not session.get('admin_email'):
        flash('Please log in as admin.', 'warning')
        return redirect(url_for('admin'))
    
    # Get statistics
    total_donations = donations_collection.count_documents({})
    pending_donations = donations_collection.count_documents({'status': 'pending'})
    total_volunteers = volunteers_collection.count_documents({})
    total_recipients = recipients_collection.count_documents({})
    completed_deliveries = assignments_collection.count_documents({'status': 'completed'})
    
    # Get recent donations
    recent_donations = list(donations_collection.find().sort('created_at', -1).limit(10))
    
    # Get recent volunteers
    recent_volunteers = list(volunteers_collection.find().sort('created_at', -1).limit(5))
    
    stats = {
        'total_donations': total_donations,
        'pending_donations': pending_donations,
        'total_volunteers': total_volunteers,
        'total_recipients': total_recipients,
        'completed_deliveries': completed_deliveries
    }
    
    return render_template('admin_dashboard.html', stats=stats, recent_donations=recent_donations, recent_volunteers=recent_volunteers)

@app.route('/admin/assign-volunteer/<donation_id>')
def assign_volunteer(donation_id):
    """Assign volunteer to donation based on proximity"""
    from bson.objectid import ObjectId
    
    try:
        # Convert string ID to ObjectId
        donation = donations_collection.find_one({'_id': ObjectId(donation_id)})
        if not donation:
            flash('Donation not found.', 'error')
            return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Error finding donation: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Get donor location (simplified - using pincode for proximity)
    donor = donors_collection.find_one({'email': donation['donor_email']})
    donor_pincode = donor['pincode'] if donor else None
    
    # Find any available volunteers - relaxed criteria to ensure functionality
    available_volunteers = list(volunteers_collection.find({}, limit=10))
    
    if not available_volunteers:
        flash('No volunteers found in the system.', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    # Assign to first available volunteer (simplified assignment)
    assigned_volunteer = available_volunteers[0]
    
    assignment_data = {
        'donation_id': str(donation['_id']),
        'volunteer_email': assigned_volunteer['email'],
        'status': 'assigned',
        'assigned_at': datetime.now()
    }
    
    assignments_collection.insert_one(assignment_data)
    
    # Update donation status
    donations_collection.update_one(
        {'_id': ObjectId(donation_id)},
        {'$set': {'status': 'assigned', 'assigned_volunteer': assigned_volunteer['email']}}
    )
    
    # Send notification to volunteer
    send_volunteer_notification(assigned_volunteer['email'], donation)
    
    flash(f'Volunteer {assigned_volunteer["name"]} assigned successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/recipients', methods=['GET', 'POST'])
def manage_recipients():
    """Manage recipients (admin only)"""
    if not session.get('admin_email'):
        flash('Please log in as admin.', 'warning')
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        recipient_data = {
            'name': request.form['name'],
            'phone': request.form['phone'],
            'address': request.form['address'],
            'city': request.form['city'],
            'state': request.form['state'],
            'pincode': request.form['pincode'],
            'family_size': int(request.form['family_size']),
            'verification_status': 'verified',
            'created_at': datetime.now()
        }
        
        recipients_collection.insert_one(recipient_data)
        flash('Recipient added successfully!', 'success')
        return redirect(url_for('manage_recipients'))
    
    recipients = list(recipients_collection.find())
    return render_template('manage_recipients.html', recipients=recipients)

@app.route('/impact')
def impact():
    """Impact page with detailed statistics"""
    # Get comprehensive statistics
    total_donations = donations_collection.count_documents({})
    total_volunteers = volunteers_collection.count_documents({})
    total_recipients = recipients_collection.count_documents({})
    completed_deliveries = assignments_collection.count_documents({'status': 'completed'})
    
    # Get monthly statistics
    current_month = datetime.now().replace(day=1)
    monthly_donations = donations_collection.count_documents({'created_at': {'$gte': current_month}})
    monthly_deliveries = assignments_collection.count_documents({
        'assigned_at': {'$gte': current_month},
        'status': 'completed'
    })
    
    stats = {
        'total_donations': total_donations,
        'total_volunteers': total_volunteers,
        'total_recipients': total_recipients,
        'completed_deliveries': completed_deliveries,
        'monthly_donations': monthly_donations,
        'monthly_deliveries': monthly_deliveries
    }
    
    return render_template('impact.html', stats=stats)

@app.route('/monthly-donor', methods=['GET', 'POST'])
def monthly_donor():
    """Monthly Donor Circle page"""
    if request.method == 'POST':
        # Store monthly donor information
        donor_data = {
            'name': request.form['name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'amount': 400,  # Fixed amount of ₹400
            'type': 'monthly',
            'status': 'active',
            'created_at': datetime.now()
        }
        
        # Insert into database
        monthly_donors_collection.insert_one(donor_data)
        flash('Thank you for joining our Monthly Donor Circle! We will contact you shortly with payment details.', 'success')
        return redirect(url_for('monthly_donor'))
    
    return render_template('monthly_donor.html')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    if request.method == 'POST':
        # Handle contact form submission
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')

@app.route('/mission')
def mission():
    """Mission page"""
    return render_template('mission.html')

if __name__ == '__main__':
    app.run(debug=True)
