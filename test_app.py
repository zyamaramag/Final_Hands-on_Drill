import unittest
from app import app, User
from flask import url_for
import os
import shutil
import tempfile
from io import BytesIO
import pickle
from passlib.hash import sha512_crypt

class TestApp(unittest.TestCase):
    def setUp(self):
        # Create a test client
        self.app = app.test_client()
        self.app.testing = True
        
        # Create necessary directories
        os.makedirs('db/contents', exist_ok=True)
        
        # Create test database with hashed passwords
        self.test_db = {
            'testuser': sha512_crypt.hash('password'),
            'otheruser': sha512_crypt.hash('password')
        }
        with open('db/db.pickle', 'wb') as f:
            pickle.dump(self.test_db, f)
        
        # Create test content log
        with open('db/content-log.log', 'w') as f:
            f.write('test_image.jpg???:???Wed Mar 20 10:00:00 2024???:???testuser???:???Test caption\n')
        
        # Create test image
        with open('db/contents/test_image.jpg', 'wb') as f:
            f.write(b'fake image content')

    def tearDown(self):
        # Clean up test files
        if os.path.exists('db/contents/test_image.jpg'):
            os.remove('db/contents/test_image.jpg')
        if os.path.exists('db/content-log.log'):
            os.remove('db/content-log.log')
        if os.path.exists('db/db.pickle'):
            os.remove('db/db.pickle')
        if os.path.exists('db/contents'):
            shutil.rmtree('db/contents')
        if os.path.exists('db'):
            shutil.rmtree('db')

    def test_index_route(self):
        """Test the index route redirects to login when not authenticated"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/login' in response.location)

    def test_login_page(self):
        """Test the login page loads correctly"""
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Account Login', response.data)

    def test_signup_page(self):
        """Test the signup page loads correctly"""
        response = self.app.get('/signup/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign Up', response.data)

    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = self.app.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })
        self.assertIn(b'Invalid Credentials', response.data)

    def test_signup_validation(self):
        """Test signup validation rules"""
        # Test username with spaces
        response = self.app.post('/signup/', data={
            'username': 'test user',
            'password0': 'password123',
            'password1': 'password123'
        })
        self.assertIn(b'Username cannot contain spaces', response.data)

        # Test non-matching passwords
        response = self.app.post('/signup/', data={
            'username': 'testuser',
            'password0': 'password123',
            'password1': 'different'
        })
        self.assertIn(b'Passwords must Match', response.data)

    def test_home_route_protection(self):
        """Test that home route is protected"""
        response = self.app.get('/home')
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/login' in response.location)

    def test_login(self):
        """Test successful login"""
        response = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome', response.data)

    def test_home_route(self):
        """Test home route after login"""
        # First login
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        })
        
        # Then test home route
        response = self.app.get('/home')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome', response.data)
        self.assertIn(b'testuser', response.data)

    def test_view_post(self):
        """Test viewing a post"""
        # First login
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        })
        
        # Test viewing an existing post
        response = self.app.get('/view-post/test_image.jpg')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Post by testuser', response.data)
        self.assertIn(b'Test caption', response.data)
        self.assertIn(b'Edit Caption', response.data)
        
        # Test viewing a non-existent post
        response = self.app.get('/view-post/nonexistent.jpg')
        self.assertEqual(response.status_code, 302)

    def test_view_post_edit_button(self):
        """Test edit button visibility based on ownership"""
        # Login as testuser
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        })
        
        # View own post - should see edit button
        response = self.app.get('/view-post/test_image.jpg')
        self.assertIn(b'Edit Caption', response.data)
        
        # Logout
        self.app.get('/logout/')
        
        # Login as different user
        self.app.post('/login', data={
            'username': 'otheruser',
            'password': 'password'
        })
        
        # View someone else's post - should not see edit button
        response = self.app.get('/view-post/test_image.jpg')
        self.assertNotIn(b'Edit Caption', response.data)

    def test_upload_file(self):
        """Test file upload functionality"""
        # First login
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        })
        
        # Create a test file
        test_file = (BytesIO(b'test file content'), 'test.jpg')
        
        # Upload the file
        response = self.app.post('/uploader/',
            data={
                'meme-file': test_file,
                'caption-text': 'Test upload caption'
            },
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify file was created
        self.assertTrue(os.path.exists('db/contents/test.jpg'))
        
        # Verify content log was updated
        with open('db/content-log.log', 'r') as f:
            content = f.read()
            self.assertIn('test.jpg', content)
            self.assertIn('Test upload caption', content)

    def test_edit_caption(self):
        """Test caption editing functionality"""
        # First login
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        })
        
        # Test editing caption
        response = self.app.post('/edit-caption/test_image.jpg',
            data={'new_caption': 'Updated caption'},
            follow_redirects=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify caption was updated
        with open('db/content-log.log', 'r') as f:
            content = f.read()
            self.assertIn('Updated caption', content)

    def test_delete_post(self):
        """Test post deletion functionality"""
        # First login
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        })
        
        # Test deleting own post
        response = self.app.post('/delete-post/test_image.jpg', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify post was deleted from content log
        with open('db/content-log.log', 'r') as f:
            content = f.read()
            self.assertNotIn('test_image.jpg', content)
        
        # Verify file was deleted
        self.assertFalse(os.path.exists('db/contents/test_image.jpg'))

    def test_upload_video(self):
        """Test video upload functionality"""
        # First login
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        })
        
        # Create a test video file
        test_file = (BytesIO(b'test video content'), 'test.mp4')
        
        # Upload the video
        response = self.app.post('/uploader/',
            data={
                'meme-file': test_file,
                'caption-text': 'Test video upload'
            },
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify video was created
        self.assertTrue(os.path.exists('db/contents/test.mp4'))
        
        # Verify content log was updated
        with open('db/content-log.log', 'r') as f:
            content = f.read()
            self.assertIn('test.mp4', content)
            self.assertIn('Test video upload', content)

if __name__ == '__main__':
    unittest.main() 