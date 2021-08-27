import os
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    db.execute("DROP TABLE ind")
    db.execute("CREATE TABLE ind (symbol TEXT, share INTEGER, price INTEGER, value INTEGER)")
    ab = db.execute("SELECT DISTINCT symbol FROM txn WHERE id = ?", session["user_id"])
    l = len(ab)
    tv = 0;
    for i in range(l):
        n = db.execute("SELECT SUM(share) FROM txn WHERE id = ? AND symbol = ? AND type = ?", session["user_id"], ab[i]['symbol'], "BUY")
        s = db.execute("SELECT SUM(share) FROM txn WHERE id = ? AND symbol = ? AND type = ?", session["user_id"], ab[i]['symbol'], "SELL")
        
        if (s[0]["SUM(share)"]) == None:
            abss = int(n[0]["SUM(share)"])
        else:
            abss = int(n[0]["SUM(share)"]) - int(s[0]["SUM(share)"])
        if (abss) < 1:
            break
        p = lookup(ab[i]['symbol'])
        mp = int(p['price'])  * abss
        tv = mp + tv
        db.execute("INSERT INTO ind (symbol,share,price,value) VALUES(?,?,?,?)", ab[i]['symbol'], abss, usd(p['price']), usd(mp))


    database = db.execute("SELECT * FROM ind")
    cas = db.execute ("SELECT cash FROM users WHERE id = ?", session["user_id"])

    return render_template("index.html", database=database, cashdata=usd(cas[0]['cash']), stockvalue=usd(tv))




@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    if request.method == "POST":
        if request.form.get("symbol") == "":
            return apology("Enter stock you want to buy")
        if request.form.get("shares") == "":
            return apology("Enter number of shares you want to buy")

        a = (request.form.get("shares"))



        if a.isdigit():
            print("LETSGOOO")
        else:
            return apology("Decimal numbers")



        curr = lookup(request.form.get("symbol"))

        if curr == None:
            return apology("INVALID SYMBOL")

        curp = int((curr["price"]))
        ca = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        now = datetime.now()

        current_time = now.strftime("%Y-%m-%d %H:%M:%S")

        for dicts in ca:
            for keys in dicts:
                cash = float(dicts[keys])
        chk = curp*(int(request.form.get("shares")))
        if chk > cash:
            return apology("Not enough money")
        else:
            db.execute("INSERT INTO txn (id, symbol, share, price, time, type ) VALUES (?, ?, ?, ?, ?, ?) ", session["user_id"], request.form.get("symbol"), request.form.get("shares"), usd(curp), current_time, "BUY")
            cash = cash - chk
            db.execute("UPDATE users SET cash = ? WHERE id = ?",cash, session["user_id"])


            return redirect("/")




@app.route("/money", methods = ["GET", "POST"])
@login_required
def money():
    if request.method == "GET":
        return render_template("money.html")
    else:
        m = request.form.get("money")
        mm = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        
        cash = int(m) + int(mm[0]['cash'])
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])
        return redirect("/")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    database = db.execute("SELECT * FROM txn WHERE id = ? AND (type = ? OR type = ?) ORDER BY time DESC", session["user_id"], "BUY", "SELL")
    return render_template("history.html", database = database)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()


    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quoted.html")
    else:
        sym = request.form.get("symbol")
        if request.form.get("symbol") == "":
            return apology("Enter stock you want to buy")

        st = lookup(sym)
        if st == None:
            return apology("INVALID SYMBOL")
        return render_template("quote.html", stockname = st["name"], name = st["symbol"], price = usd(st["price"]))




@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("enter username")
        user =  request.form.get("username")
        asss = db.execute("SELECT id FROM users WHERE username = ?", user)
        if  asss:
            return apology("USERNAME ALREADY TAKEN")
        
        if not request.form.get("password"):
            return apology("enter password")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if password != confirmation:
            return apology("Password don't match")

        hashed = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)",user,hashed)
        rows = db.execute("SELECT id FROM users WHERE username = ?", user)
        session["user_id"] = rows[0]["id"]
        return redirect("/")
        
        
       
    else:
        return render_template("register.html")





@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        sh = db.execute("SELECT DISTINCT symbol FROM txn WHERE id = ? AND type = ?", session["user_id"], "BUY")
        return render_template("sell.html", database = sh)


    else:
        if request.form.get("symbol") == None:
            return apology("Forgot to select stock")

        if request.form.get("shares") == "":
            return apology("INVALID NUMBER OF SHARES ENTERED!")


        if int(request.form.get("shares")) < 1:
            return apology("INVALID NUMBER OF SHARES ENTERED!")

        ab = request.form.get("symbol")
        abn = request.form.get("shares")

        asb = db.execute("SELECT SUM(share) FROM txn WHERE id = ? AND symbol = ? AND type = ?",session["user_id"], ab, "BUY")
        ns = int(asb[0]["SUM(share)"])
        if int(abn)>ns:
            return apology("No. Of shares entered exceed shares owned")

        st = lookup(ab)
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        db.execute("INSERT INTO txn (id, symbol, share, price, time, type) VALUES(?, ?, ?, ?,?, ?)", session["user_id"], ab, abn, usd(st["price"]), current_time, "SELL")
        
        mone = db.execute("SELECT cash FROM users WHERE id = ?",session["user_id"])
        for dicts in mone:
            for keys in dicts:
                cash = float(dicts[keys])
        cash = cash + (int(st["price"]) * int(abn) )

        db.execute("UPDATE users SET cash = ? WHERE id = ?",cash ,session["user_id"])


        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
