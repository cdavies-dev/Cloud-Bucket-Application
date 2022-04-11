#IMPORTS
from sys import hash_info
import yagmail
import secrets
import sqlite3
import os.path
from os import urandom
from hashlib import md5
import mysql.connector
from binascii import hexlify, unhexlify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivymd.app import MDApp

#KV SCREENS
class LoginScreen(Screen):
    pass

class RegisterScreen(Screen):
    pass

class TokenScreen(Screen):
    pass

class HomeScreen(Screen):
    pass

class UploadScreen(Screen):
    pass

class DownloadScreen(Screen):
    pass

#CLASSES
class Application(MDApp):
    def build(self) -> None:
        #define screen manager
        self.smgr = ScreenManager()
        
        #set kivy theme
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'BlueGray'

        #set kivy properties for reuse
        self.screen_width = 500
        self.screen_height = 1000
        self.widget_width = 400
        self.image_width = 300

        return Builder.load_file('styles.kv')
    
    def register(self) -> None:
        db, cursor = self.db_init()

        #pull name and email from app  
        reg_name = self._running_app.root.ids.register.ids.name.text
        reg_email = self._running_app.root.ids.register.ids.email.text

        cursor.execute(f'SELECT email FROM user_info WHERE email = "{reg_email}"')
        result = cursor.fetchone()

        #if True, account exists, else create account and send token to email, clear fields
        if result:
            self._running_app.root.ids.register.ids.reg_txt.text = 'Account already exists!'
            self._running_app.root.ids.register.ids.name.text = ''
            self._running_app.root.ids.register.ids.email.text = ''
        else:
            self._running_app.root.ids.register.ids.reg_txt.text = 'Registration successful!'
            token = secrets.token_urlsafe(16)

            yagmail.SMTP('SENDER EMAIL HERE', 'PASSWORD HERE').send(reg_email, 'PyAuth Token', token)
            file = open('token.txt', 'w')
            file.write(token)

            cursor.execute(f'INSERT INTO user_info VALUES ("{reg_name}", "{reg_email}", "{token}")')
            db.commit()
            db.close()

            self.root.transition.direction = 'left'
            self.root.current = 'home'
            self._running_app.root.ids.register.ids.name.text = ''
            self._running_app.root.ids.register.ids.email.text = ''

    def login(self) -> None:
        #check for existing account token
        token_exists = os.path.exists('token.txt')

        #pull name and email from app
        self.user_name = self._running_app.root.ids.login.ids.name.text
        self.user_email = self._running_app.root.ids.login.ids.email.text

        #if login details are blank display text
        if(self.user_name == '') or (self.user_email == '' ) or (self.user_name == '' and self.user_email == ''):
            self.root.ids.login.ids.log_txt.text = 'Incorrect details provided!'
            #--- EXPAND TO ACCOUNT FOR INCORRECT INFORMATION            
        else:
            #if account token exists, check details against database  
            if token_exists:
                file = open('token.txt', 'r')
                file_token = file.read()
                
                db, cursor = self.db_init()
        
                cursor.execute(f'SELECT token FROM user_info WHERE name = "{self.user_name}" AND email = "{self.user_email}"')
                db_token = cursor.fetchall()
                db_token = db_token[0] #convert from list    
                db_token = db_token[0] #convert from tuple

                cursor.execute(f'SELECT name FROM user_info WHERE token = "{db_token}" AND email = "{self.user_email}"')
                db_name = cursor.fetchall()
                db_name = db_name[0]    
                db_name = db_name[0]

                cursor.execute(f'SELECT email FROM user_info WHERE token = "{db_token}" AND name = "{self.user_name}"')
                db_email = cursor.fetchall()
                db_email = db_email[0]    
                db_email = db_email[0]

                db.commit()
                db.close()

                if (file_token == db_token) and (self.user_name == db_name) and (self.user_email == db_email):
                    #accept login, move to home screen
                    self.root.transition.direction = 'left'
                    self.root.current = 'home'
                else:
                    self.root.ids.login.ids.log_txt.text = 'Incorrect details provided!'
            else:
                #move to token screen
                self.root.transition.direction = 'left' 
                self.root.current = 'token'

    def logout(self) -> None:
        #move to login screen // HOME SCREEN NOT ACCESSIBLE WITHOUT AUTH
        self.root.transition.direction = 'right'
        self.root.current = 'login'
        self.clear()

    def token_verification(self) -> None:
        #pull token from app
        user_token = self._running_app.root.ids.token.ids.token_txt.text
        
        db, cursor = self.db_init()

        cursor.execute(f'SELECT token FROM user_info WHERE name = "{self.user_name}" AND email = "{self.user_email}"')
        db_token = cursor.fetchall()
        db_token = db_token[0] #convert from list    
        db_token = db_token[0] #convert from tuple

        db.commit()
        db.close()

        #if token matches database, move to home screen, create token.txt and clear fields
        if user_token == db_token:
            self.root.transition.direction = 'left'
            self.root.current = 'home'
            file = open('token.txt', 'w')
            file.write(db_token)
            self._running_app.root.ids.login.ids.name.text = ''
            self._running_app.root.ids.login.ids.email.text = ''
            self.user_name = ''
            self.user_email = ''
        else:
            self._running_app.root.ids.token.ids.token_lbl.text = 'Token does not match!'

    def db_init(self) -> tuple:
        #premised db and cursor init
        db = sqlite3.connect('local.db')
        cursor = db.cursor()

        return db, cursor

    def gcloud_init(self) -> tuple:
        #remote db and cursor init
        gcloud = mysql.connector.connect(user = 'USER HERE', password = 'PASSWORD HERE', host = 'BUCKET IP HERE', database = 'BUCKET DATABASE HERE')
        cursor = gcloud.cursor(buffered = True)

        return gcloud, cursor

    def clear(self) -> None:
        #clear fields
        self._running_app.root.ids.login.ids.name.text = ''
        self._running_app.root.ids.login.ids.email.text = ''

    def upload(self) -> None:
        gcloud, gg_cursor = self.gcloud_init()
        lcl_db, lcl_cursor = self.db_init()

        #pull name and course from app
        student_name = self._running_app.root.ids.upload.ids.name.text
        student_course = self._running_app.root.ids.upload.ids.course.text

        #--- INMPLEMENT AES ENCRYPTION + RESULT HEXLIFICATION (EXC. THROWN IN DOWNLOAD())
        #key = urandom(16)
        #iv = urandom(16)
        #encrypted_name, encrypted_course = self.aes_encrypt(key, iv, student_name, student_course)
        #hex_name, hex_course = hexlify(encrypted_name), hexlify(encrypted_course)

        #generate md5 hash based on name+course concat
        to_hash = bytes(str(student_name + student_course), 'utf-8')
        encryption_hash = md5(to_hash).hexdigest()

        gg_cursor.execute(f'INSERT INTO entries (student_name, course) VALUES ("{student_name}","{student_course}")')
        gcloud.commit()
        gg_cursor.execute(f'SELECT student_id FROM entries WHERE student_name = "{student_name}" AND course = "{student_course}"')
        gcloud.commit()

        student_id = gg_cursor.fetchall()
        student_id = student_id[0] #convert from list    
        student_id = student_id[0] #convert from tuple

        #--- IMPLEMENT PREMISED STORAGE FOR AES KEY, IV AND HASH VALUES
        #lcl_cursor.execute(f'INSERT INTO encryption_info (id, key, init_vector, hash) VALUES ("{student_id}","{key}","{iv}","{encryption_hash}")')
        #lcl_db.commit()

        self._running_app.root.ids.upload.ids.upload_lbl.text = 'Upload successful!'
        self._running_app.root.ids.upload.ids.new_id_name_lbl.text = f'Student ID for {student_name} is st{student_id}'
        self._running_app.root.ids.upload.ids.name.text = ''
        self._running_app.root.ids.upload.ids.course.text = ''

        lcl_db.close()
        gcloud.close()
    
    def download(self) -> None:
        gcloud, gg_cursor = self.gcloud_init()
        #lcl_db, lcl_cursor = self.db_init()
        
        #pull student ID from app
        student_id = self._running_app.root.ids.download.ids.stnum_lbl.text

        gg_cursor.execute(f'SELECT student_name FROM entries WHERE student_id = "{student_id}"')
        gcloud.commit()

        student_name = gg_cursor.fetchall()
        student_name = student_name[0] #convert from list    
        student_name = student_name[0] #convert from tuple

        gg_cursor.execute(f'SELECT course FROM entries WHERE student_id = "{student_id}"')
        gcloud.commit()

        student_course = gg_cursor.fetchall()
        student_course = student_course[0]    
        student_course = student_course[0]

        #--- IMPLEMENT PREMISED STORAGE FOR AES KEY, IV AND HASH VALUES
        #lcl_cursor.execute(f'SELECT key FROM encryption_info WHERE id = "{student_id}"')
        #lcl_db.commit()

        #key = lcl_cursor.fetchall()
        #key = key[0]    
        #key = key[0]

        #lcl_cursor.execute(f'SELECT init_vector FROM encryption_info WHERE id = "{student_id}"')
        #lcl_db.commit()

        #iv = lcl_cursor.fetchall()
        #iv = iv[0]    
        #iv = iv[0]

        #lcl_cursor.execute(f'SELECT hash FROM encryption_info WHERE id = "{student_id}"')
        #lcl_db.commit()

        #stored_hash = lcl_cursor.fetchall()
        #stored_hash = stored_hash[0]   
        #stored_hash = stored_hash[0]

        #to_hash = hex_name + hex_course
        #regenerated_hash = md5(to_hash).hexdigest()

        #encrypted_name, encrypted_course = unhexlify(hex_name), unhexlify(hex_course) --- PRODUCES ODD LENGTH STR EXCEPT, not returning bytes object
            
        #decrypted_name, decrypted_course = self.aes_decrypt(key, iv, encrypted_name, encrypted_course) --- PRODUCES INCORRECT KEY LENGTH EXCEPT

        #--- IMPLEMENT IF HASH MATCH SEND INFORMATION TO APP
        #if str(regenerated_hash) == stored_hash:
        self._running_app.root.ids.download.ids.dl_id_lbl.text = f'Displaying information for st{student_id}'
        self._running_app.root.ids.download.ids.dl_name_lbl.text = f'Name: {student_name}'
        self._running_app.root.ids.download.ids.dl_course_lbl.text = f'Course: {student_course}'
        self._running_app.root.ids.download.ids.stnum_lbl.text = ''
        #else:
        #self._running_app.root.ids.download.ids.dl_id_lbl.text = 'UNAUTHORISED ACCESS'   
        #self._running_app.root.ids.download.ids.dl_name_lbl.text = 'UNAUTHORISED ACCESS'
        #self._running_app.root.ids.download.ids.dl_course_lbl.text = 'UNAUTHORISED ACCESS'
        #self._running_app.root.ids.download.ids.stnum_lbl.text = ''
        
        #lcl_db.close()
        gcloud.close()

    def aes_encrypt(self, key, iv, name, course) -> tuple:
        name_bytes = bytes(str(name), 'utf-8')
        name_padded = pad(name_bytes, AES.block_size)
        AES_obj = AES.new(key, AES.MODE_CBC, iv)
        enc_name = AES_obj.encrypt(name_padded)

        course_bytes = bytes(str(course), 'utf-8')
        course_padded = pad(course_bytes, AES.block_size)
        AES_obj = AES.new(key, AES.MODE_CBC, iv)
        enc_course = AES_obj.encrypt(course_padded)

        return enc_name, enc_course

    def aes_decrypt(self, key, iv, enc_name, enc_course) -> tuple:
        AES_obj = AES.new(key, AES.MODE_CBC, iv)
        enc_name_padded = AES_obj.decrypt(enc_name)
        dec_name = unpad(enc_name_padded, AES.block_size).decode('ascii')

        AES_obj = AES.new(key, AES.MODE_CBC, iv)
        enc_course_padded = AES_obj.decrypt(enc_course)
        dec_course = unpad(enc_course_padded, AES.block_size).decode('ascii')

        return dec_name, dec_course

#MAIN      
def main():
    Window.maximize()
    Window.fullscreen = True
    Application().run()

if __name__ == '__main__':
    main()