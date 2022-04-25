from flask import request, redirect, url_for, flash, render_template, abort
from app import app, db
from werkzeug.utils import secure_filename
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from forms import LoginForm, RegisterForm, TweetForm
from flask_login import LoginManager
from models import User, Tweet, followers
from flask_login import login_required, login_user, current_user, logout_user

login_manager = LoginManager(app)
login_manager.login_view = 'login'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def follow_suggest_list(user):
    return User.query.filter(User.id != user.id).order_by(db.func.random()).limit(4).all()


def upload_image(file, username):
    if file is None:
        flash('No image selected for uploading')
        return redirect(request.url)
    if file.filename == '':
        flash('No image selected for uploading')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filename = username + "_" + filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # print('upload_image filename: ' + filename)
        # flash('Image successfully uploaded and displayed below')
        # return render_template('upload.html', filename=filename)
    else:
        flash('Allowed image types are -> png, jpg, jpeg, gif')
        return redirect(request.url)
    return filename


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    pass
    return render_template('index.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Username does not exist', 'danger')
            return redirect(url_for('login'))
        if check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('You need to logout first to register', 'danger')
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.username.data
        user = User.query.filter_by(username=name).first()
        if user:
            flash('Username already taken', 'danger')
            return redirect(url_for('register'))
        if form.image.data:
            image_filename = form.image.data
            filename = upload_image(image_filename, str(name))
            img_url = os.path.join(app.config['IMAGE_FOLDER'], filename)
            print(img_url)
        else:
            img_url = img_url = os.path.join(app.config['IMAGE_FOLDER'], 'img.png')
        password = generate_password_hash(form.password.data)
        new_user = User(
            name=form.name.data,
            username=name,
            password=password,
            image=img_url,
            join_date=datetime.now(),
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('profile'))

    return render_template('register.html', form=form)


@app.route('/profile', defaults={'username': None})
@app.route('/profile/<username>')
@login_required
def profile(username):
    form = TweetForm()
    if username:
        user = User.query.filter_by(username=username).first()
        if not user:
            abort(404)
        # tweets = Tweet.query.filter_by(user=user).order_by(Tweet.date_created.desc()).all()
        # total_tweets = len(tweets)
    else:
        user = current_user
    tweets = Tweet.query.filter_by(user=user).order_by(Tweet.date_created.desc()).all()
        # tweets = Tweet.query.join(followers, (followers.c.followee_id == Tweet.user_id)).filter(
        #     followers.c.follower_id == current_user.id).order_by(Tweet.date_created.desc()).all()
        # total_tweets = Tweet.query.filter_by(user=user).order_by(Tweet.date_created.desc()).count()

    followed_by = user.followed_by.all()


    display_follow = True

    if current_user == user:
        display_follow = False
    elif current_user in followed_by:
        display_follow = False

    current_time = datetime.now()
    follow_suggestions = follow_suggest_list(user)

    return render_template('profile.html', current_user=user, form=form, tweets=tweets, current_time=current_time,
                           display_follow=display_follow, followed_by=followed_by, follow_suggestions=follow_suggestions)


@app.route('/timeline', defaults={'username' : None})
@app.route('/timeline/<username>')
def timeline(username):
    form = TweetForm()

    if username:
        user = User.query.filter_by(username=username).first()
        if not user:
            abort(404)

        tweets = Tweet.query.filter_by(user=user).order_by(Tweet.date_created.desc()).all()
        total_tweets = len(tweets)

    else:
        user = current_user
        tweets = Tweet.query.join(followers, (followers.c.followee_id == Tweet.user_id)).filter(followers.c.follower_id == current_user.id).order_by(Tweet.date_created.desc()).all()
        total_tweets = Tweet.query.filter_by(user=user).order_by(Tweet.date_created.desc()).count()

    current_time = datetime.now()

    followed_by_count = user.followed_by.count()

    follow_suggestions = follow_suggest_list(user)

    return render_template('timeline.html', form=form, tweets=tweets, current_time=current_time, current_user=user,
                           total_tweets=total_tweets, logged_in_user=current_user,
                           followed_by_count=followed_by_count, follow_suggestions=follow_suggestions)


@app.route('/post_tweet', methods=['GET', 'POST'])
@login_required
def post_tweet():
    form = TweetForm()

    if form.validate():
        tweet = Tweet(user_id=current_user.id, text=form.text.data, date_created=datetime.now())
        db.session.add(tweet)
        db.session.commit()

        return redirect(url_for('profile'))

    return render_template('post_tweet.html', form=form)


@app.route('/follow/<username>')
@login_required
def follow(username):
    user_to_follow = User.query.filter_by(username=username).first()

    current_user.following.append(user_to_follow)

    db.session.commit()

    return redirect(url_for('profile'))