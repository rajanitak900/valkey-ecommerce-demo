import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCart, updateCartItem, removeCartItem } from '../helper/api'

const CartSection = () => {
  const [cart, setCart] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")

  useEffect(() => {
    async function loadCart() {
      try {
        const response = await getCart()
        setCart(response)
      } catch (err) {
        setError(err.message || 'Unable to load cart. Please log in.')
      } finally {
        setLoading(false)
      }
    }
    loadCart()
  }, [])

  const handleQuantityChange = async (productId, quantity) => {
    try {
      await updateCartItem(productId, quantity)
      const response = await getCart()
      setCart(response)
      setMessage('Cart updated successfully')
    } catch (err) {
      setError(err.message || 'Unable to update quantity')
    }
  }

  const handleRemoveItem = async (productId) => {
    try {
      await removeCartItem(productId)
      const response = await getCart()
      setCart(response)
      setMessage('Item removed from cart')
    } catch (err) {
      setError(err.message || 'Unable to remove item')
    }
  }

  if (loading) {
    return (
      <section className="cart py-80">
        <div className="container container-lg text-center">Loading cart...</div>
      </section>
    )
  }

  if (error) {
    return (
      <section className="cart py-80">
        <div className="container container-lg">
          <div className="alert alert-danger mb-24">{error}</div>
          <div className="text-center">
            <Link to="/account" className="btn btn-main py-18 w-100 rounded-8">
              Log in to view your cart
            </Link>
          </div>
        </div>
      </section>
    )
  }

  const items = cart?.items || []
  const subtotal = cart?.subtotal || 0
  const total = cart?.total || subtotal

  return (
    <section className="cart py-80">
      <div className="container container-lg">
        {message && <div className="alert alert-success mb-24">{message}</div>}
        <div className="row gy-4">
          <div className="col-xl-9 col-lg-8">
            <div className="cart-table border border-gray-100 rounded-8 px-40 py-48">
              <div className="overflow-x-auto scroll-sm scroll-sm-horizontal">
                <table className="table style-three">
                  <thead>
                    <tr>
                      <th className="h6 mb-0 text-lg fw-bold">Remove</th>
                      <th className="h6 mb-0 text-lg fw-bold">Product</th>
                      <th className="h6 mb-0 text-lg fw-bold">Price</th>
                      <th className="h6 mb-0 text-lg fw-bold">Quantity</th>
                      <th className="h6 mb-0 text-lg fw-bold">Subtotal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="text-center py-40">
                          Your cart is empty.
                        </td>
                      </tr>
                    ) : (
                      items.map((item) => (
                        <tr key={item.product.id}>
                          <td>
                            <button
                              type="button"
                              onClick={() => handleRemoveItem(item.product.id)}
                              className="remove-tr-btn flex-align gap-12 hover-text-danger-600"
                            >
                              <i className="ph ph-x-circle text-2xl d-flex" /> Remove
                            </button>
                          </td>
                          <td>
                            <div className="table-product d-flex align-items-center gap-24">
                              <Link
                                to={`/product-details?product_id=${encodeURIComponent(item.product.id)}`}
                                className="table-product__thumb border border-gray-100 rounded-8 flex-center "
                              >
                                <img src={item.product.image_url || 'assets/images/thumbs/product-two-img1.png'} alt={item.product.name} />
                              </Link>
                              <div className="table-product__content text-start">
                                <h6 className="title text-lg fw-semibold mb-8">
                                  <Link to={`/product-details?product_id=${encodeURIComponent(item.product.id)}`} className="link text-line-2">
                                    {item.product.name}
                                  </Link>
                                </h6>
                                <span className="text-gray-600 text-sm">{item.product.brand || 'Store Item'}</span>
                              </div>
                            </div>
                          </td>
                          <td>
                            <span className="text-lg h6 mb-0 fw-semibold">${item.product.price?.toFixed(2) || '0.00'}</span>
                          </td>
                          <td>
                            <div className="cart-quantity d-flex align-items-center gap-8">
                              <button
                                type="button"
                                onClick={() => handleQuantityChange(item.product.id, Math.max(1, item.quantity - 1))}
                                className="btn btn-small btn-outline"
                              >
                                -
                              </button>
                              <span className="text-lg fw-semibold">{item.quantity}</span>
                              <button
                                type="button"
                                onClick={() => handleQuantityChange(item.product.id, item.quantity + 1)}
                                className="btn btn-small btn-outline"
                              >
                                +
                              </button>
                            </div>
                          </td>
                          <td>
                            <span className="text-lg h6 mb-0 fw-semibold">${item.line_total?.toFixed(2) || '0.00'}</span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div className="col-xl-3 col-lg-4">
            <div className="cart-sidebar border border-gray-100 rounded-8 px-24 py-40">
              <h6 className="text-xl mb-32">Cart Totals</h6>
              <div className="bg-color-three rounded-8 p-24">
                <div className="mb-32 flex-between gap-8">
                  <span className="text-gray-900 font-heading-two">Subtotal</span>
                  <span className="text-gray-900 fw-semibold">${subtotal.toFixed(2)}</span>
                </div>
                <div className="mb-32 flex-between gap-8">
                  <span className="text-gray-900 font-heading-two">Estimated Delivery</span>
                  <span className="text-gray-900 fw-semibold">Free</span>
                </div>
                <div className="mb-0 flex-between gap-8">
                  <span className="text-gray-900 font-heading-two">Estimated Tax</span>
                  <span className="text-gray-900 fw-semibold">${(total - subtotal).toFixed(2)}</span>
                </div>
              </div>
              <div className="bg-color-three rounded-8 p-24 mt-24">
                <div className="flex-between gap-8">
                  <span className="text-gray-900 text-xl fw-semibold">Total</span>
                  <span className="text-gray-900 text-xl fw-semibold">${total.toFixed(2)}</span>
                </div>
              </div>
              <Link to="/checkout" className="btn btn-main mt-40 py-18 w-100 rounded-8">
                Proceed to checkout
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default CartSection