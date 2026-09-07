from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from datetime import datetime

news_bp = Blueprint('news', __name__)

NEWS_POSTS = [
    {
        "id": 1,
        "title": "Welcome to CheepCards Arcades!",
        "content": "We've officially launched the Mana Mash-up puzzle engine. Test your sequencing skills and climb the ladder!",
        "author": "Admin",
        "date": "2026-08-26",
        "poll": {
            "id": 1,
            "question": "Which puzzle archetype is your favorite?",
            "options": {"Storm Combos": 12, "Reanimation": 8, "Artifact Loops": 15},
            "voted": False
        }
    }
]

@news_bp.route('/news')
def public_news():
    search_query = request.args.get('q', '').strip().lower()
    filtered_posts = NEWS_POSTS
    
    if search_query:
        filtered_posts = [
            p for p in NEWS_POSTS 
            if search_query in p['title'].lower() or search_query in p['content'].lower()
        ]
        
    return render_template('news_public.html', posts=filtered_posts, search_query=request.args.get('q', ''))

@news_bp.route('/news/vote/<int:poll_id>', methods=['POST'])
def vote_poll(poll_id):
    selected_option = request.form.get('option')
    for post in NEWS_POSTS:
        if post.get("poll") and post["poll"]["id"] == poll_id:
            if selected_option in post["poll"]["options"]:
                post["poll"]["options"][selected_option] += 1
                post["poll"]["voted"] = True
                flash("Vote recorded successfully!", "success")
            else:
                flash("Invalid poll option selected.", "danger")
    return redirect(url_for('news.public_news'))

@news_bp.route('/admin/news', methods=['GET', 'POST'])
@login_required
def admin_news():
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)
        
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        has_poll = request.form.get('has_poll')
        
        new_post = {
            "id": max([p["id"] for p in NEWS_POSTS], default=0) + 1,
            "title": title,
            "content": content,
            "author": getattr(current_user, 'username', 'Admin'),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "poll": None
        }
        
        if has_poll:
            question = request.form.get('poll_question')
            opt1 = request.form.get('opt1')
            opt2 = request.form.get('opt2')
            options = {}
            if opt1: options[opt1] = 0
            if opt2: options[opt2] = 0
            if question and options:
                new_post["poll"] = {
                    "id": new_post["id"],
                    "question": question,
                    "options": options,
                    "voted": False
                }
                
        NEWS_POSTS.insert(0, new_post)
        flash("News post published successfully!", "success")
        return redirect(url_for('news.admin_news'))
        
    return render_template('news_admin.html', posts=NEWS_POSTS)

@news_bp.route('/admin/news/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_news(post_id):
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)

    post = next((p for p in NEWS_POSTS if p["id"] == post_id), None)
    if not post:
        flash("Post not found.", "danger")
        return redirect(url_for('news.admin_news'))
        
    if request.method == 'POST':
        post['title'] = request.form.get('title')
        post['content'] = request.form.get('content')
        
        has_poll = request.form.get('has_poll')
        if has_poll:
            question = request.form.get('poll_question')
            opt1 = request.form.get('opt1')
            opt2 = request.form.get('opt2')
            
            existing_poll = post.get("poll", {})
            existing_options = existing_poll.get("options", {}) if existing_poll else {}
            voted_status = existing_poll.get("voted", False) if existing_poll else False
            
            options = {}
            if opt1: 
                options[opt1] = existing_options.get(opt1, 0)
            if opt2: 
                options[opt2] = existing_options.get(opt2, 0)
                
            if question and options:
                post["poll"] = {
                    "id": post["id"],
                    "question": question,
                    "options": options,
                    "voted": voted_status
                }
        else:
            post["poll"] = None
            
        flash("Post updated successfully!", "success")
        return redirect(url_for('news.admin_news'))
        
    return render_template('news_edit.html', post=post)

@news_bp.route('/admin/news/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_news(post_id):
    if getattr(current_user, 'role', None) != 'admin':
        abort(403)
        
    global NEWS_POSTS
    post = next((p for p in NEWS_POSTS if p["id"] == post_id), None)
    if not post:
        flash("Post not found.", "danger")
        return redirect(url_for('news.admin_news'))
        
    NEWS_POSTS = [p for p in NEWS_POSTS if p["id"] != post_id]
    flash("News post and associated poll deleted successfully.", "success")
    return redirect(url_for('news.admin_news'))