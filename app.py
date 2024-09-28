from flask import Flask, redirect,render_template,request,session
from flask_session import Session
import sqlite3
import base64
import matplotlib.pyplot as plt
import io

app = Flask(__name__)
app.secret_key = 'navneet'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = "filesystem"
Session(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

data = sqlite3.connect("database.db", check_same_thread=False)
data.execute("""
             create table if not exists users(
             id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
             username TEXT NOT NULL UNIQUE, 
             password TEXT NOT NULL, 
             role TEXT NOT NULL);
             """)
data.execute("""
             create table if not exists flagged_users(
             id INTEGER NOT NULL ,
             username TEXT NOT NULL);
             """)
data.execute("""
             create table if not exists flagged_campaigns(
             id INTEGER NOT NULL ,
             camp_name TEXT NOT NULL);
             """)
data.execute("""
             create table if not exists ratings(
             id INTEGER NOT NULL,
             rating INTEGER NOT NULL,
             from_id INTEGER NOT NULL,
             PRIMARY KEY (from_id, id) );
             """)
data.execute("""
             create table if not exists doing(
              id INTEGER NOT NULL ,
              campaign_id INTEGER NOT NULL);
             """)
data.execute("""
             create table if not exists all_campaigns(
              id INTEGER NOT NULL UNIQUE,
              name TEXT NOT NULL,
              hosted_by TEXT NOT NULL);
             """)
data.execute("""
             create table if not exists completed(
              id INTEGER NOT NULL ,
              campaign_id INTEGER NOT NULL);
             """)
data.execute("""
             create table if not exists campaigns(
              id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              hosted_by INTEGER NOT NULL,
              budget INTEGER NOT NULL
              );
             """)
data.execute("""
             create table if not exists images(
              id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
              image BLOB NOT NULL);
             """)
data.execute("""
             create table if not exists requests(
               from_id INTEGER NOT NULL,
               to_id INTEGER NOT NULL,
               PRIMARY KEY (from_id, to_id) 
             );
             """)
data.execute("""
             create table if not exists total_requests(
               id INTEGER NOT NULL PRIMARY KEY,
               requests INTEGER NOT NULL,
               campaigns INTEGER NOT NULL
             );
             """)
data.execute("""
             create table if not exists camp_requests(
               from_id INTEGER NOT NULL,
               to_id INTEGER NOT NULL,
               PRIMARY KEY (from_id, to_id) 
             );
             """)
data.execute("""
             create table if not exists bios(
              id INTEGER NOT NULL,
              bio TEXT NOT NULL);
             """)
data.execute("""
             create table if not exists expense(
               camp_id INTEGER NOT NULL,
               expense INTEGER NOT NULL
             );""")
cursor = data.cursor()


try:
  cursor.execute("insert into users (id,username,password,role) values(?,?,?,?)",(1,"Admin",'myhero12','admin'))
  data.commit()
except sqlite3.IntegrityError:
  pass


@app.route('/',methods=["GET","POST"])
def index():
  if request.method == "POST":
    if 'log_out' in request.form:
      session.clear()
      return redirect("/")
    try:
      username= request.form["username"]
      password= request.form["password"]
      cursor.execute("select username from flagged_users")
      flagged_users = cursor.fetchall()
      for i in flagged_users:
        if i[0] == username:
          return render_template("index.html",flag=True,flag2=False)
      
      role = request.form["role"]
      cursor.execute("insert into users(username,password,role) values(?,?,?)",(username,password,role,))
      data.commit()
      cursor.execute("""INSERT INTO total_requests (id,requests,campaigns)
                  VALUES ((select id from users where username=?),0,0)""",(username,))
      if role == "influencer":
        bio = request.form["bio"]
        cursor.execute("insert into bios(id,bio) values((select id from users where username = ?),?)",(username,bio,))
        data.commit()
        data.commit()
      return render_template("index.html",flag=False,flag2=True)
    except sqlite3.IntegrityError:
      return render_template("index.html",flag=True,flag2=False)
  return render_template("index.html",flag=False)

@app.route('/register_inf',methods=["GET","POST"])
def register_inf():
  return render_template("register_inf.html")

@app.route('/register_spo',methods=["GET","POST"])
def register_spo():
  return render_template("register_spo.html")

@app.route('/dashboard',methods=["GET","POST"])
def dashboard():
  if request.method == "POST":
    id = 0
    username= request.form["username"]
    cursor.execute('SELECT password,role,id FROM users where username = ?',(username,))
    rows = cursor.fetchall()
    for row in rows:
      if row[1] == "admin":
        name = username
        cursor.execute("select * from campaigns where name not in (select camp_name from flagged_campaigns) and id in (select campaign_id from doing)")
        data_admin = cursor.fetchall()
        cursor.execute("select * from flagged_users")
        flagged_users = cursor.fetchall()
        cursor.execute("select * from flagged_campaigns")
        flagged_campaigns = cursor.fetchall()
        return render_template("admin_dashboard.html",data=data_admin,flagged_users=flagged_users,flagged_campaigns=flagged_campaigns,name=name)
      id = row[2]# dont know why isnt it working without loop
      if username in session or (row[0] == request.form["password"]):

        session[username] = True
        if 'completed' in request.form:
          camp_id = request.form['camp_id']
          try:
            cursor.execute("insert into completed(id,campaign_id) values(?,?)",(id,camp_id))
            data.commit()
            cursor.execute("delete from doing where id = ? and campaign_id = ? ",(id,camp_id))
            data.commit()
            cursor.execute("""UPDATE total_requests
                        SET campaigns = campaigns + 1
                        WHERE id = ?;""",(id,))
            data.commit()
            cursor.execute("""UPDATE total_requests
                        SET campaigns = campaigns + 1
                        WHERE id = (select hosted_by from campaigns where id = ?);""",(camp_id))
            cursor.execute("""Update expense set expense = expense + (select budget from campaigns where id = ?) where camp_id = ?""",(camp_id,camp_id))
          except sqlite3.IntegrityError:
            pass
        if 'reject' in request.form:
          camp_id = request.form['reject']
          cursor.execute("delete from requests where from_id = ? and to_id = ? ",(camp_id,id))
          data.commit()
        if 'accept' in request.form:
          camp_id = request.form['accept']
          cursor.execute("insert into doing(id,campaign_id) values(?,?)",(id,camp_id))
          data.commit()
          cursor.execute("delete from requests where from_id = ? and to_id = ? ",(camp_id,id))
          data.commit()
        if 'reject2' in request.form:
          camp_id = request.form['reject2']
          inf_id = request.form['inf_id']
          cursor.execute("delete from camp_requests where from_id = ? and to_id = ? ",(inf_id,camp_id))
          data.commit()
        if 'accept2' in request.form:
          camp_id = request.form['accept2']
          inf_id = request.form['inf_id']
          cursor.execute("insert into doing(id,campaign_id) values(?,?)",(inf_id,camp_id))
          data.commit()
          cursor.execute("delete from camp_requests where from_id = ? and to_id = ? ",(inf_id,camp_id))
          data.commit()
          
        if 'flag2' in request.form:
          if 'file' not in request.files:
            return 'No file part'
            
          file = request.files['file']
            
          if file.filename == '':
            return 'No selected file'
            
          if file and allowed_file(file.filename):
              file_content = file.read()
              cursor.execute('delete from images where id = ?',(request.form['id'],))
              data.commit()
              cursor.execute('insert into images("id","image") values(?,?)',(request.form['id'],file_content,))
              data.commit()
              
        if 'flag' in request.form:
          if request.form['flag'] == "true":
            camp_name = request.form["camp_name"]
            cursor.execute("""
                          insert into campaigns("name","hosted_by")
                          values(?,?);
                          """,(camp_name,id))
            data.commit()
        if 'edit' in request.form:
          bio_edit = request.form["edit"]
          cursor.execute('delete from bios where id = ?',(row[2],))
          data.commit()
          cursor.execute('insert into bios(id,bio) values (?,?)',(row[2],bio_edit,))
          data.commit()
        
        
        if row[1] == "admin":
          cursor.execute("select * from all_campaigns")
          data_admin = cursor.fetchall()
          cursor.execute("select * from flagged_users")
          flagged_users = cursor.fetchall()
          cursor.execute("select * from flagged_campaigns")
          flagged_campaigns = cursor.fetchall()
          return render_template("admin_dashboard.html",data=data_admin,flagged_users=flagged_users,flagged_campaigns=flagged_campaigns)
        if row[1] == "influencer":
          cursor.execute('Select AVG(rating) from ratings where id = ?',(row[2],))
          rating_rows =cursor.fetchall()
          avg_rating = 0
          rating = " "
          for rating_row in rating_rows:
            try:
              avg_rating = int(rating_row[0])
              rating = "⭐"*avg_rating
            except TypeError:
              rating = "None"
          cursor.execute('Select image from images where id = ?',(row[2],))
          image_rows =cursor.fetchall()
          encoded_image = []
          
          for image_row in image_rows:
            image = image_row[0]
            encoded_image = base64.b64encode(image).decode("utf-8")
          if encoded_image == []:
            with open("image.png", 'rb') as image_file:
              binary_data = image_file.read()
              base64_encoded_data = base64.b64encode(binary_data)
              encoded_image = base64_encoded_data.decode('utf-8')
          data_camp=[]
          cursor.execute('Select name,id from campaigns where id IN (select campaign_id from doing where id = ?)',(row[2],))
          data_camp = cursor.fetchall()
          data_completed=[]
          cursor.execute('Select name,id from campaigns where id IN (select campaign_id from completed where id = ?)',(row[2],))
          data_completed = cursor.fetchall()
          data_requests=[]
          cursor.execute('Select name,id from campaigns where id = (select from_id from requests where to_id = ?)',(row[2],))
          data_requests =cursor.fetchall()
          bio = "NO BIO"
          cursor.execute('Select bio from bios where id = ?',(row[2],))
          bio = cursor.fetchone()
          try:
            bio=bio[0]
          except TypeError:
            bio = "NO BIO"  
          return render_template("influencer_dashboard.html",name=username,rating=rating,image=encoded_image,id=id,data=data_camp,data_requests = data_requests,bio=bio,data_completed=data_completed)
        if row[1] == "sponsor":
          active=[]
          cursor.execute('Select name,id from campaigns where hosted_by = ?  and id in (select campaign_id from doing)',(row[2],))
          active = cursor.fetchall()
          requests=[]
          cursor.execute("""
                          SELECT 
                              u.username,
                              cr.from_id,
                              c.name AS campaign_name,
                              c.id
                          FROM 
                              camp_requests cr
                          JOIN 
                              users u ON cr.from_id = u.id
                          JOIN 
                              campaigns c ON cr.to_id = c.id
                          WHERE 
                              c.hosted_by = ?;

                        """
                         ,(row[2],))
          
        requests =cursor.fetchall()
        
        return render_template("sponsor_dashboard.html",name=username,id=id,active=active,requests = requests)
  return "<h1>Wrong username or password.</h1>"

@app.route('/campaigns', methods=['POST'])
def campaigns():
  id = request.form["id"]
  name= request.form["name"]
  if 'remove' in request.form:
    camp_id = request.form["camp_id"]
    cursor.execute("delete from campaigns where id =?",(camp_id,))
    data.commit()
    data_camp=[]
    cursor.execute("select name,id from campaigns where hosted_by = ?",(id,))
    data_camp = cursor.fetchall()
    return render_template("campaigns.html",id=id,name=name,data=data_camp)
  if request.form['flag'] == "true":
    camp_name = request.form["camp_name"]
    budget = request.form["budget"]
    cursor.execute("select camp_name from flagged_campaigns")
    flagged_camps = cursor.fetchall()
    for i in flagged_camps:
      if i[0] == camp_name:
        data_camp=[]
        cursor.execute("select name,id from campaigns where hosted_by = ?",(id,))
        data_camp = cursor.fetchall()
        return render_template("campaigns.html",id=id,name=name,data=data_camp)
    cursor.execute("""
                   insert into campaigns("name","hosted_by","budget")
                   values(?,?,?);
                   """,(camp_name,id,budget))
    cursor.execute("""
                   insert into all_campaigns("id","name","hosted_by")
                   values((select id from campaigns where name = ?),?,?);
                   """,(camp_name,camp_name,id))
    data.commit()
    cursor.execute("""
                   insert into expense(camp_id,expense)
                   values((select id from campaigns where name = ?),0);
                   """,(camp_name,))
  data_camp=[]
  cursor.execute("select name,id from campaigns where hosted_by = ?",(id,))
  data_camp = cursor.fetchall()
  return render_template("campaigns.html",id=id,name=name,data=data_camp)


@app.route("/find",methods=['POST'])
def find():
  flag= "-1"
  name = ""
  id = request.form['id']
  data_camp=[]
  if 'request' in request.form:
    name = request.form["username"]
    camp_id = request.form['request']
    try:
      cursor.execute("insert into camp_requests(from_id,to_id) values(?,?)",(id,camp_id))
      cursor.execute("""UPDATE total_requests
                        SET requests = requests + 1
                        WHERE id = (select hosted_by from campaigns where id = ?);""",(camp_id,))
      data.commit()
      flag="0"
    except sqlite3.IntegrityError:
      flag="1"
    cursor.execute('SELECT name,id FROM campaigns')
    data_camp = cursor.fetchall()
  elif 'flag' in request.form:
    search = request.form["search"]
    name = request.form["name"]
    cursor.execute("select name,id from campaigns where name like ?",('%'+search+'%',))
    data_camp = cursor.fetchall()
  else:
    name=request.form["name"]
    cursor.execute('SELECT name,id FROM campaigns ')
    data_camp = cursor.fetchall()
  

  if session[name]:
    return render_template("find.html",data=data_camp,name=name,id=id,flag=flag)
  else:
    return redirect("/")
  
@app.route("/view_camp",methods=['POST'])
def view_camp():
  camp_id = request.form['camp_id']
  data_camp=[]
  cursor.execute("select * from campaigns where id = ?",(camp_id,))
  data_camp = cursor.fetchall()
  host_id = data_camp[0][2]
  cursor.execute("select username from users where id = ?",(host_id,))
  host = cursor.fetchall()
  cursor.execute("select username from users where id = (select id from doing where campaign_id = ?)",(camp_id,))
  inf=cursor.fetchall()
  if inf == []:
    inf = [["NOT ASSIGNED YET"]]
  
  return render_template("view_camp.html",data=data_camp,host=host,inf=inf)

@app.route("/find_infl",methods=['POST'])
def find_infl():
  flag= "-1"
  name = ""
  id = request.form['id']
  data_camp=[]
  camp_id=request.form['camp_id']
  if 'request' in request.form:
    name = request.form["username"]
    try:
      inf_id =request.form["inf_id"]
      cursor.execute("insert into requests(from_id,to_id) values(?,?)",(camp_id,inf_id))
      data.commit()
      cursor.execute("""UPDATE total_requests
                        SET requests = requests + 1
                        WHERE id = ?;""",(inf_id,))
      data.commit()
      flag="0"
    except sqlite3.IntegrityError:
      flag="1"
    cursor.execute('SELECT username,id FROM users where role = ?',('influencer',))
    data_camp = cursor.fetchall()
  elif 'flag' in request.form:
    search = request.form["search"]
    name = request.form["username"]
    cursor.execute("select username,id from users where username like ? and role = ?",('%'+search+'%','influencer'))
    data_camp = cursor.fetchall()
  else:
    if 'rating' in request.form:
      inf_id =request.form["inf_id"]
      rating = request.form['rating']
      try:
        cursor.execute("INSERT INTO ratings (id, rating, from_id) VALUES (?, ?,?)", (inf_id, rating,id))
        data.commit()
      except sqlite3.IntegrityError:
        cursor.execute("UPDATE ratings SET rating = ? WHERE id = ? AND from_id = ?", (rating, inf_id, id))
        data.commit()
    name=request.form["username"]
    cursor.execute('SELECT username,id FROM users where role = ?',('influencer',))
    data_camp = cursor.fetchall()
  

  if session[name]:
    return render_template("find_infl.html",data=data_camp,name=name,id=id,flag=flag,camp_id=camp_id)
  else:
    return redirect("/")
  




def get_user_stats(user_id, role):

    if role == 'sponsor':
      cursor.execute("""
          SELECT COUNT(DISTINCT d.id) 
          FROM doing d
          JOIN campaigns c ON d.campaign_id = c.id
          WHERE c.hosted_by = ?
      """, (user_id,))
      num_influencers = cursor.fetchone()[0]

      try:
        cursor.execute("SELECT requests FROM total_requests WHERE id = ?", (user_id,))
        num_requests = cursor.fetchone()[0]
      except TypeError:
        pass



      cursor.execute("""
        select camp_id,expense from expense where camp_id IN (select id from all_campaigns where hosted_by =?)
        """, (user_id,))
      
      total_spent = cursor.fetchall()
      total_spent_name = []
      for i in total_spent:
        cursor.execute("select name from all_campaigns where id = ?",(i[0],))
        total_spent_name.append((cursor.fetchall()[0][0],i[1]))
      print(total_spent)
      cursor.execute("SELECT campaigns FROM total_requests WHERE id = ?", (user_id,))
      num_campaigns = cursor.fetchone()[0]

      stats = [{
          'Number of Influencers': num_influencers,
          'Total Requests': num_requests,
          'Total Campaigns': num_campaigns
      },total_spent_name]
      print(stats)


    elif role == 'influencer':
        cursor.execute("SELECT campaign_id FROM doing WHERE id = ?", (user_id,))
        campaigns = cursor.fetchall()

        cursor.execute("SELECT AVG(rating) FROM ratings WHERE id = ?", (user_id,))
        avg_rating = cursor.fetchone()[0]
        
        num_requests=0
        try:
          cursor.execute("SELECT requests FROM total_requests WHERE id = ?", (user_id,))
          num_requests = cursor.fetchone()[0]
        except TypeError:
          pass

        cursor.execute("SELECT bio FROM bios WHERE id = ?", (user_id,))
        bio = cursor.fetchone()[0]

        cursor.execute("SELECT campaigns FROM total_requests WHERE id = ?", (user_id,))
        num_campaigns = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(budget) FROM campaigns WHERE id IN (SELECT campaign_id FROM completed WHERE id = ?)", (user_id,))
        avg_campaign_budget = cursor.fetchone()[0]

        """cursor.execute("SELECT COUNT(*) FROM doing WHERE id = ? AND campaign_id IN (SELECT id FROM campaigns WHERE status = 'completed')", (user_id,))
        num_completed_campaigns = cursor.fetchone()[0]"""

        cursor.execute("SELECT rating, COUNT(*) FROM ratings WHERE id = ? GROUP BY rating", (user_id,))
        ratings_distribution = cursor.fetchall()
        
        stats = [{
            'Average Rating': avg_rating,
            'Number of Requests': num_requests,
            'Bio': bio,
            'Number of Campaigns': num_campaigns,
            'Average Campaign Budget': avg_campaign_budget,
            #'Number of Completed Campaigns': num_completed_campaigns,
        },ratings_distribution]

    return stats

def plot_stats(stats, user_role):
    plt.figure(figsize=(10, 6))

    if user_role == 'sponsor':
        ratings_dist = stats
        try:
          if not ratings_dist:
              plt.figure(figsize=(10, 6))
              plt.text(0.5, 0.5, 'No Data Available', fontsize=20, ha='center', va='center', color='gray')
              plt.xlabel('No Campaigns')
              plt.ylabel('No Campaigns')
              plt.title('Expense Distribution')
          else:
              ratings_labels = [str(r[0]) for r in ratings_dist]
              ratings_values = [r[1] for r in ratings_dist]
              plt.pie(ratings_values, labels=ratings_labels, autopct='%1.1f%%', startangle=140, wedgeprops=dict(width=0.3))
              plt.title('Expense Distribution')
              plt.gca().set_aspect('equal') 
        except:
          plt.figure(figsize=(10, 6))
          plt.text(0.5, 0.5, 'No Data Available', fontsize=20, ha='center', va='center', color='gray')
          plt.xlabel('No Campaigns')
          plt.ylabel('No Campaigns')
          plt.title('Expense Distribution')

    elif user_role == 'influencer':

        # Plot Ratings Distribution
      ratings_dist = stats
      if stats==[]:
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, 'No Data Available', fontsize=20, ha='center', va='center', color='gray')
        plt.xlabel('No Ratings')
        plt.ylabel('No Count')
        plt.title('Ratings Distribution')
      else:
          plt.figure(figsize=(10, 6))
          ratings_labels = [str(r[0]) for r in ratings_dist]
          ratings_values = [r[1] for r in ratings_dist]
          plt.bar(ratings_labels, ratings_values, color='purple')
          plt.xlabel('Ratings')
          plt.ylabel('Count')
          plt.title('Ratings Distribution')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()

    return img_base64

@app.route('/stats', methods=['POST'])
def stats():
    name = request.form.get('name')
    if(name == 'Admin'):
      stats = {}
      cursor.execute("select count(*) from users")
      stats["Total Users"] = cursor.fetchone()[0]
      cursor.execute("select count(*) from all_campaigns")
      stats["Total Campaigns"] = cursor.fetchone()[0]
      cursor.execute("select count(name) from campaigns where id in (select campaign_id from doing)")
      stats["Active Campaigns"] = cursor.fetchone()[0]
      cursor.execute("select sum(requests) from total_requests")
      stats["Total requests to influencers"] = cursor.fetchone()[0]
      return render_template("admin_stats.html",stats=stats)
    user_id = request.form.get('id')
    
    if user_id and name:
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        role = cursor.fetchone()[0]

        user_stats = get_user_stats(user_id, role)
        
        if user_stats:
            img_base64 = plot_stats(user_stats[1], role)
            return render_template('stats.html', name=name, stats=user_stats[0],img_base64=img_base64)
        else:
            return "No stats found for the user."
    return "Invalid user ID or name."

@app.route("/find_adm",methods=['POST'])
def find_adm():
  name=request.form["name"]
  data_camp=[]
  data_inf=[]
  if 'flag' in request.form:
    if 'inf_id' in request.form:
      id = request.form["inf_id"]
      cursor.execute("insert into flagged_users(id,username) values(?,(select username from users where id = ?))",(id,id))
      data.commit()
      cursor.execute("delete from users where id = ?",(id,))
      data.commit()
    if 'camp_id' in request.form:
      id = request.form["camp_id"]
      cursor.execute("insert into flagged_campaigns(id,camp_name) values(?,(select name from campaigns where id = ?))",(id,id))
      data.commit()
      cursor.execute("delete from campaigns where id = ?",(id,))
      data.commit()
    cursor.execute('SELECT name,id FROM campaigns where id not in (select id from flagged_campaigns)')
    data_camp = cursor.fetchall()
    cursor.execute('SELECT username,id FROM users where id not in (select id from flagged_users) ')
    data_inf = cursor.fetchall()
    data_inf = data_inf[1:]
  elif 'search' in request.form:
    search = request.form["search"]
    cursor.execute("select name,id from campaigns where name like ?",('%'+search+'%',))
    data_camp = cursor.fetchall()
    cursor.execute('SELECT username,id FROM users where username like ? ',('%'+search+'%',))
    data_inf = cursor.fetchall()
    
  else:
    cursor.execute('SELECT name,id FROM campaigns where id not in (select id from flagged_campaigns)')
    data_camp = cursor.fetchall()
    cursor.execute('SELECT username,id FROM users where id not in (select id from flagged_users) ')
    data_inf = cursor.fetchall()
    data_inf = data_inf[1:]
  
  return render_template("find_adm.html",campaigns=data_camp,influencers=data_inf,name=name)

  


app.run(port=8000)

data.close()

