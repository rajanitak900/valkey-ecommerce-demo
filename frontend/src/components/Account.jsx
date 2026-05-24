import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { login, register, saveToken } from '../helper/api'

const Account = () => {
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [registerName, setRegisterName] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const handleLogin = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      const tokenResponse = await login(loginEmail, loginPassword)
      saveToken(tokenResponse.access_token)
      setMessage('Login successful! You can now use the cart and checkout.')
    } catch (err) {
      setError(err.message || 'Login failed')
    }
  }

  const handleRegister = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      await register(registerName, registerEmail, registerPassword)
      setMessage('Registration successful! Please log in below.')
      setRegisterName('')
      setRegisterEmail('')
      setRegisterPassword('')
    } catch (err) {
      setError(err.message || 'Registration failed')
    }
  }

  return (
    <section className="account py-80">
      <div className="container container-lg">
        {message && <div className="alert alert-success mb-24">{message}</div>}
        {error && <div className="alert alert-danger mb-24">{error}</div>}
        <div className="row gy-4">
          <div className="col-xl-6 pe-xl-5">
            <div className="border border-gray-100 hover-border-main-600 transition-1 rounded-16 px-24 py-40 h-100">
              <h6 className="text-xl mb-32">Login</h6>
              <form onSubmit={handleLogin}>
                <div className="mb-24">
                  <label htmlFor="loginEmail" className="text-neutral-900 text-lg mb-8 fw-medium">
                    Email address <span className="text-danger">*</span>
                  </label>
                  <input
                    type="email"
                    className="common-input"
                    id="loginEmail"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="Enter your email"
                    required
                  />
                </div>
                <div className="mb-24">
                  <label htmlFor="loginPassword" className="text-neutral-900 text-lg mb-8 fw-medium">
                    Password
                  </label>
                  <div className="position-relative">
                    <input
                      type="password"
                      className="common-input"
                      id="loginPassword"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="Enter password"
                      required
                    />
                    <span
                      className="toggle-password position-absolute top-50 inset-inline-end-0 me-16 translate-middle-y cursor-pointer ph ph-eye-slash"
                      id="#loginPassword"
                    />
                  </div>
                </div>
                <div className="mb-24 mt-48">
                  <div className="flex-align gap-48 flex-wrap">
                    <button type="submit" className="btn btn-main py-18 px-40">
                      Log in
                    </button>
                    <div className="form-check common-check">
                      <input className="form-check-input" type="checkbox" id="remember" />
                      <label className="form-check-label flex-grow-1" htmlFor="remember">
                        Remember me
                      </label>
                    </div>
                  </div>
                </div>
                <div className="mt-48">
                  <Link to="#" className="text-danger-600 text-sm fw-semibold hover-text-decoration-underline">
                    Forgot your password?
                  </Link>
                </div>
              </form>
            </div>
          </div>
          <div className="col-xl-6">
            <div className="border border-gray-100 hover-border-main-600 transition-1 rounded-16 px-24 py-40">
              <h6 className="text-xl mb-32">Register</h6>
              <form onSubmit={handleRegister}>
                <div className="mb-24">
                  <label htmlFor="registerName" className="text-neutral-900 text-lg mb-8 fw-medium">
                    Name <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    className="common-input"
                    id="registerName"
                    value={registerName}
                    onChange={(e) => setRegisterName(e.target.value)}
                    placeholder="Enter your name"
                    required
                  />
                </div>
                <div className="mb-24">
                  <label htmlFor="registerEmail" className="text-neutral-900 text-lg mb-8 fw-medium">
                    Email address <span className="text-danger">*</span>
                  </label>
                  <input
                    type="email"
                    className="common-input"
                    id="registerEmail"
                    value={registerEmail}
                    onChange={(e) => setRegisterEmail(e.target.value)}
                    placeholder="Enter Email Address"
                    required
                  />
                </div>
                <div className="mb-24">
                  <label htmlFor="registerPassword" className="text-neutral-900 text-lg mb-8 fw-medium">
                    Password <span className="text-danger">*</span>
                  </label>
                  <div className="position-relative">
                    <input
                      type="password"
                      className="common-input"
                      id="registerPassword"
                      value={registerPassword}
                      onChange={(e) => setRegisterPassword(e.target.value)}
                      placeholder="Enter Password"
                      required
                    />
                    <span
                      className="toggle-password position-absolute top-50 inset-inline-end-0 me-16 translate-middle-y cursor-pointer ph ph-eye-slash"
                      id="#registerPassword"
                    />
                  </div>
                </div>
                <div className="my-48">
                  <p className="text-gray-500">
                    Your personal data will be used to process your order, support your experience throughout this website, and for other purposes described in our
                    <Link to="#" className="text-main-600 text-decoration-underline">
                      {' '}
                      privacy policy
                    </Link>
                    .
                  </p>
                </div>
                <div className="mt-48">
                  <button type="submit" className="btn btn-main py-18 px-40">
                    Register
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Account