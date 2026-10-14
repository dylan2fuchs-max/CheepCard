from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
from Card_Filter import db
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

news_bp = Blueprint('news', __name__)

# --- DATABASE MODELS FOR NEWS, POLLS & FEEDBACK ---
class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='General')
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    viewed = db.Column(db.Boolean, default=False)
    viewed_by = db.Column(db.String(100), nullable=True)

class NewsPost(db.Model):
    __tablename__ = 'news_posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    
    # Relationship to poll (one-to-one)
    poll = db.relationship('Poll', backref='post', uselist=False, cascade='all, delete-orphan')

class Poll(db.Model):
    __tablename__ = 'polls'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('news_posts.id'), nullable=False)
    question = db.Column(db.String(300), nullable=False)
    # Storing options and vote counts as a JSON dictionary: {"Option A": 5, "Option B": 2}
    options = db.Column(db.JSON, nullable=False, default=dict)
    # Stored as a comma-separated string or tracked per user if desired, keeping simple session/voted flag per request or tracking
    voted = db.Column(db.Boolean, default=False) 


@news_bp.route('/news')
def public_news():
    search_query = request.args.get('q', '').strip().lower()
    
    # Query all posts from PostgreSQL, newest first
    query = NewsPost.query.order_by(NewsPost.id.desc())
    posts = query.all()
    
    if search_query:
        posts = [
            p for p in posts 
            if search_query in p.title.lower() or search_query in p.content.lower()
        ]
        
    return render_template('news_public.html', posts=posts, search_query=request.args.get('q', ''))

@news_bp.route('/news/vote/<int:poll_id>', methods=['POST'])
def vote_poll(poll_id):
    selected_option = request.form.get('option')
    poll = Poll.query.get_or_404(poll_id)
    
    options = dict(poll.options) if poll.options else {}
    if selected_option in options:
        options[selected_option] += 1
        poll.options = options
        poll.voted = True
        db.session.commit()
        flash("Vote recorded successfully!", "success")
    else:
        flash("Invalid poll option selected.", "danger")
        
    return redirect(url_for('news.public_news'))

@news_bp.route('/news/feedback', methods=['GET', 'POST'])
def feedback_page():
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        
        if not message:
            flash("Feedback message cannot be empty.", "danger")
            return redirect(url_for('news.feedback_page'))
            
        username = current_user.username if current_user.is_authenticated else "Guest User"
        email = getattr(current_user, 'email', None) or "guest@cheepcards.local"
        category = "General"
        
        try:
            new_feedback = Feedback(
                username=username,
                email=email,
                category=category,
                message=message,
                viewed=False
            )
            db.session.add(new_feedback)
            db.session.commit()
            
            # Optional: Email notification logic
            smtp_server = os.environ.get('MAIL_SERVER')
            smtp_port = int(os.environ.get('MAIL_PORT', 587))
            smtp_user = os.environ.get('MAIL_USERNAME')
            smtp_pass = os.environ.get('MAIL_PASSWORD')
            admin_email = os.environ.get('ADMIN_EMAIL', smtp_user)
            
            if smtp_server and smtp_user and smtp_pass:
                msg = MIMEMultipart()
                msg['From'] = smtp_user
                msg['To'] = admin_email
                msg['Subject'] = f"New CheepCards Feedback from {username}"
                body = f"Category: {category}\nUser: {username} ({email})\n\nMessage:\n{message}"
                msg.attach(MIMEText(body, 'plain'))
                
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                    
            flash("Thank you for your feedback! It has been successfully recorded.", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to save feedback: {e}")
            flash("An error occurred while saving your feedback. Please try again.", "danger")
            
        return redirect(url_for('news.public_news'))
        
    return render_template('feedback.html')

@news_bp.route('/admin/news', methods=['GET', 'POST'])
@login_required
def admin_news():
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)
        
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        has_poll = request.form.get('has_poll')
        
        new_post = NewsPost(
            title=title,
            content=content,
            author=getattr(current_user, 'username', 'Admin'),
            date=datetime.now().strftime("%Y-%m-%d")
        )
        db.session.add(new_post)
        db.session.flush() # Flush to get new_post.id for the poll foreign key
        
        if has_poll:
            question = request.form.get('poll_question')
            opt1 = request.form.get('opt1')
            opt2 = request.form.get('opt2')
            opt3 = request.form.get('opt3')
            opt4 = request.form.get('opt4')
            options = {}
            if opt1: options[opt1] = 0
            if opt2: options[opt2] = 0
            if opt3: options[opt3] = 0
            if opt4: options[opt4] = 0
            
            if question and options:
                new_poll = Poll(
                    post_id=new_post.id,
                    question=question,
                    options=options,
                    voted=False
                )
                db.session.add(new_poll)
                
        db.session.commit()
        flash("News post published successfully!", "success")
        return redirect(url_for('news.admin_news'))
        
    posts = NewsPost.query.order_by(NewsPost.id.desc()).all()
    return render_template('news_admin.html', posts=posts)

@news_bp.route('/admin/news/feedback')
@login_required
def view_feedback():
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)
        
    feedbacks = Feedback.query.order_by(Feedback.date.desc()).all()
    admin_name = getattr(current_user, 'username', 'Admin')
    updated = False
    
    for item in feedbacks:
        if not item.viewed:
            item.viewed = True
            item.viewed_by = admin_name
            updated = True
        elif not item.viewed_by:
            item.viewed_by = admin_name
            updated = True
            
    if updated:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to update feedback read status: {e}")
            
    return render_template('admin_feedback.html', feedbacks=feedbacks)

@news_bp.route('/admin/news/feedback/delete/<int:feedback_id>', methods=['POST'])
@login_required
def delete_feedback(feedback_id):
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)
        
    feedback_item = Feedback.query.get_or_404(feedback_id)
    try:
        db.session.delete(feedback_item)
        db.session.commit()
        flash("Feedback entry deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete feedback: {e}")
        flash("An error occurred while deleting feedback.", "danger")
        
    return redirect(url_for('news.view_feedback'))

@news_bp.route('/admin/news/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_news(post_id):
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)

    post = NewsPost.query.get_or_404(post_id)
        
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        
        has_poll = request.form.get('has_poll')
        if has_poll:
            question = request.form.get('poll_question')
            opt1 = request.form.get('opt1')
            opt2 = request.form.get('opt2')
            opt3 = request.form.get('opt3')
            opt4 = request.form.get('opt4')
            
            existing_options = post.poll.options if post.poll and post.poll.options else {}
            voted_status = post.poll.voted if post.poll else False
            
            options = {}
            if opt1: options[opt1] = existing_options.get(opt1, 0)
            if opt2: options[opt2] = existing_options.get(opt2, 0)
            if opt3: options[opt3] = existing_options.get(opt3, 0)
            if opt4: options[opt4] = existing_options.get(opt4, 0)
                
            if question and options:
                if post.poll:
                    post.poll.question = question
                    post.poll.options = options
                else:
                    new_poll = Poll(
                        post_id=post.id,
                        question=question,
                        options=options,
                        voted=voted_status
                    )
                    db.session.add(new_poll)
        else:
            if post.poll:
                db.session.delete(post.poll)
                post.poll = None
            
        db.session.commit()
        flash("Post updated successfully!", "success")
        return redirect(url_for('news.admin_news'))
        
    return render_template('news_edit.html', post=post)

@news_bp.route('/admin/news/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_news(post_id):
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)
        
    post = NewsPost.query.get_or_404(post_id)
    try:
        db.session.delete(post)
        db.session.commit()
        flash("News post and associated poll deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete news post: {e}")
        flash("An error occurred while deleting the post.", "danger")
        
    return redirect(url_for('news.admin_news'))