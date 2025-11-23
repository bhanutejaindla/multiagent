import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../services/auth.service';

export type UserRole = 'USER' | 'ADMIN';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css']
})
export class RegisterComponent {
  username: string = '';
  email: string = '';
  password: string = '';
  confirmPassword: string = '';
  role: UserRole = 'USER';
  errors: { [key: string]: string } = {};
  loading: boolean = false;

  constructor(
    private authService: AuthService,
    private router: Router
  ) { }

  validate(): boolean {
    this.errors = {};

    // Username validation
    if (!this.username || this.username.trim().length === 0) {
      this.errors['username'] = 'Username is required';
    } else if (this.username.trim().length < 3) {
      this.errors['username'] = 'Username must be at least 3 characters';
    } else if (!/^[a-zA-Z0-9_]+$/.test(this.username.trim())) {
      this.errors['username'] = 'Username can only contain letters, numbers, and underscores';
    }

    // Email validation
    if (!this.email || this.email.trim().length === 0) {
      this.errors['email'] = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.email.trim())) {
      this.errors['email'] = 'Please enter a valid email address';
    }

    // Password validation
    if (!this.password) {
      this.errors['password'] = 'Password is required';
    } else if (this.password.length < 6) {
      this.errors['password'] = 'Password must be at least 6 characters';
    } else if (this.password.length > 128) {
      this.errors['password'] = 'Password must be less than 128 characters';
    } else if (!/(?=.*[a-z])/.test(this.password)) {
      this.errors['password'] = 'Password must contain at least one lowercase letter';
    } else if (!/(?=.*[A-Z])/.test(this.password)) {
      this.errors['password'] = 'Password must contain at least one uppercase letter';
    } else if (!/(?=.*\d)/.test(this.password)) {
      this.errors['password'] = 'Password must contain at least one number';
    }

    // Confirm password validation
    if (!this.confirmPassword) {
      this.errors['confirmPassword'] = 'Please confirm your password';
    } else if (this.password !== this.confirmPassword) {
      this.errors['confirmPassword'] = 'Passwords do not match';
    }

    // Role validation
    if (!this.role || (this.role !== 'USER' && this.role !== 'ADMIN')) {
      this.errors['role'] = 'Please select a valid role';
    }

    return Object.keys(this.errors).length === 0;
  }

  onSubmit() {
    if (!this.validate()) {
      return;
    }

    this.loading = true;
    this.errors = {};

    this.authService.signup({
      username: this.username.trim(),
      email: this.email.trim(),
      password: this.password,
      role: this.role
    }).subscribe({
      next: () => {
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.errors['submit'] = err.error?.detail || 'Registration failed. Please try again.';
        this.loading = false;
      }
    });
  }

  getFieldError(fieldName: string): string {
    return this.errors[fieldName] || '';
  }

  hasFieldError(fieldName: string): boolean {
    return !!this.errors[fieldName];
  }
}

