from flask import render_template, jsonify
import mysql.connector
from config import Config
import bcrypt

HOST = Config.DB_HOST
USER = Config.DB_USER
PASSWORD = Config.DB_PASSWORD
DATABASE = Config.DB_NAME


def get_connection():
    return mysql.connector.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        auth_plugin='mysql_native_password',
        autocommit=True
    )


class user_model:
    def hash_password(self, password):
        return bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, plain_password, hashed_password):
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )

    def user_signup(self, data):
        con = get_connection()
        cur = con.cursor(buffered=True)

        try:
            hashed_pass = self.hash_password(data['password'])
            cur.execute(
                "INSERT INTO user_data(username, email, password_hash) "
                "VALUES (%s, %s, %s)",
                (data['username'], data['email'], hashed_pass)
            )
        finally:
            cur.close()
            con.close()

        return render_template("index.html")

    def user_login(self, data):
        con = get_connection()
        cur = con.cursor(dictionary=True, buffered=True)

        try:
            cur.execute(
                "SELECT id, username, email, password_hash "
                "FROM user_data WHERE email=%s",
                (data['email'],)
            )
            user = cur.fetchone()
        finally:
            cur.close()
            con.close()

        if not user:
            return jsonify({"message": "Invalid email or password"}), 401

        if not self.check_password(data['password'], user['password_hash']):
            return jsonify({"message": "Invalid email or password"}), 401

        return jsonify({
            "message": "Login Successful",
            "user": {
                "id": user['id'],
                "email": user['email'],
                "username": user['username']
            }
        }), 200
