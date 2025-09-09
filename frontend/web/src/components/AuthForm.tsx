// Custom authentication form with session cipher
import React, { useState } from 'react';
import { useCreateSessionMutation, useLoginMutation } from '../store/api';
import { encryptPassword, SessionResponse } from '../lib/sessionCipher';

interface AuthFormProps {
  onSuccess: () => void;
}

export const AuthForm: React.FC<AuthFormProps> = ({ onSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  const [createSession] = useCreateSessionMutation();
  const [login] = useLoginMutation();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.username.trim()) {
      newErrors.username = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.username)) {
      newErrors.username = 'Invalid email format';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }

    if (!isLogin && formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    
    try {
      if (isLogin) {
        await handleLogin();
      } else {
        await handleSignup();
      }
    } catch (error) {
      console.error('Auth error:', error);
      setErrors({ general: 'Authentication failed. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = async () => {
    try {
      // Create cipher session
      const sessionResult = await createSession().unwrap();
      
      // Encrypt password
      const cipherEnvelope = await encryptPassword({
        serverPublicKeyJwk: sessionResult.server_public_key_jwk,
        sid: sessionResult.sid,
        password: formData.password,
      });

      // Login with encrypted password
      await login({
        username: formData.username,
        cipher_envelope: {
          ...cipherEnvelope,
          sid: sessionResult.sid,
        },
      }).unwrap();

      onSuccess();
    } catch (error: any) {
      if (error.status === 401) {
        setErrors({ general: 'Invalid email or password' });
      } else {
        setErrors({ general: 'Login failed. Please try again.' });
      }
    }
  };

  const handleSignup = async () => {
    // TODO: Implement signup flow
    setErrors({ general: 'Signup not implemented yet' });
  };

  return (
    <div className="auth-form">
      <div className="auth-form-header">
        <h2>{isLogin ? 'Sign In' : 'Sign Up'}</h2>
        <p className="auth-form-subtitle">
          {isLogin ? 'Welcome back' : 'Create your account'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="auth-form-form">
        {errors.general && (
          <div className="error-message general-error">
            {errors.general}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="username">Email</label>
          <input
            type="email"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleInputChange}
            className={errors.username ? 'error' : ''}
            placeholder="Enter your email"
            disabled={isLoading}
          />
          {errors.username && (
            <span className="error-message">{errors.username}</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleInputChange}
            className={errors.password ? 'error' : ''}
            placeholder="Enter your password"
            disabled={isLoading}
          />
          {errors.password && (
            <span className="error-message">{errors.password}</span>
          )}
        </div>

        {!isLogin && (
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleInputChange}
              className={errors.confirmPassword ? 'error' : ''}
              placeholder="Confirm your password"
              disabled={isLoading}
            />
            {errors.confirmPassword && (
              <span className="error-message">{errors.confirmPassword}</span>
            )}
          </div>
        )}

        <button
          type="submit"
          className={`auth-form-submit ${isLoading ? 'loading' : ''}`}
          disabled={isLoading}
        >
          {isLoading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Sign Up')}
        </button>
      </form>

      <div className="auth-form-toggle">
        <p>
          {isLogin ? "Don't have an account?" : 'Already have an account?'}
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setErrors({});
              setFormData({ username: '', password: '', confirmPassword: '' });
            }}
            className="auth-toggle-btn"
            disabled={isLoading}
          >
            {isLogin ? 'Sign Up' : 'Sign In'}
          </button>
        </p>
      </div>

      <div className="auth-form-divider">
        <span>or</span>
      </div>

      <div className="social-login">
        <button type="button" className="social-btn google-btn" disabled={isLoading}>
          <span>Continue with Google</span>
        </button>
        <button type="button" className="social-btn facebook-btn" disabled={isLoading}>
          <span>Continue with Facebook</span>
        </button>
      </div>
    </div>
  );
};