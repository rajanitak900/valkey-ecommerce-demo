import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getProducts, addCartItem } from "../helper/api";

const ProductGrid = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function loadProducts() {
      try {
          const response = await getProducts();
          const list = Array.isArray(response)
            ? response
            : response.products || response.results || [];
          setProducts(list);
        } catch (error) {
          setMessage(error.message || "Unable to load products from backend");
        } finally {
          setLoading(false);
        }
      }
      loadProducts();
    }, []);
  const handleAddToCart = async (productId) => {
    try {
      await addCartItem(productId, 1);
      setMessage("Product added to cart. Visit Cart page to review.");
    } catch (error) {
      setMessage(error.message || "Unable to add item to cart. Please log in.");
    }
  };

  return (
    <section className="shop-grid py-40">
      <div className="container container-lg">
        <div className="d-flex justify-content-between align-items-center mb-32">
          <h2 className="title text-2xl fw-semibold">Live Products</h2>
          <span className="text-gray-600">Connected to backend API</span>
        </div>
        {message && (
          <div className="alert alert-info mb-24" role="alert">
            {message}
          </div>
        )}
        {loading ? (
          <div className="text-center py-40">Loading products...</div>
        ) : products.length === 0 ? (
          <div className="text-center py-40">No products available from backend.</div>
        ) : (
          <div className="row g-4">
            {products.map((product) => (
              <div className="col-xl-3 col-lg-4 col-md-6" key={product.id}>
                <div className="product-card h-100 p-16 border border-gray-100 hover-border-main-600 rounded-16 position-relative transition-2">
                  <Link to={`/product-details?product_id=${encodeURIComponent(product.id)}`} className="product-card__thumb flex-center rounded-8 bg-gray-50 position-relative">
                    <img
                      src={product.image_url || "assets/images/thumbs/product-two-img1.png"}
                      alt={product.name}
                      className="w-auto max-w-unset"
                    />
                    {(product.status === "best" || product.status === "active") && (
                      <span className="product-card__badge bg-primary-600 px-8 py-4 text-sm text-white position-absolute inset-inline-start-0 inset-block-start-0">
                        {product.status === "best" ? "Best Sale" : "Featured"}
                      </span>
                    )}
                  </Link>
                  <div className="product-card__content mt-16">
                    <h6 className="title text-lg fw-semibold mt-12 mb-8">
                      <Link to={`/product-details?product_id=${encodeURIComponent(product.id)}`} className="link text-line-2">
                        {product.name}
                      </Link>
                    </h6>
                    <div className="product-card__price my-20">
                      <span className="text-heading text-md fw-semibold">
                        ${product.price?.toFixed(2) || "0.00"} <span className="text-gray-500 fw-normal">/Qty</span>
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleAddToCart(product.id)}
                      className="product-card__cart btn bg-gray-50 text-heading hover-bg-main-600 hover-text-white py-11 px-24 rounded-8 flex-center gap-8 fw-medium"
                    >
                      Add To Cart <i className="ph ph-shopping-cart" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};

export default ProductGrid;
