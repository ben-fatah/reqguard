# Software Requirements Specification — StockFlow Inventory System (SYNTHETIC)

This document is synthetic. It was written for the ReqGuard benchmark and contains deliberately planted defects. It describes no real organisation.

## 1. Accounts

The system shall allow an administrator to create a user account with a name, an email address and a role.
The system shall lock a user account after 5 consecutive failed login attempts within 15 minutes.
Users should be able to reset their password.
The system shall send a password-reset link that expires 30 minutes after it is issued.
Passwords shall be stored securely.
The login page shall be user-friendly.
The system shall support the roles Administrator, Store Manager, Clerk, etc.
The system shall log out a user after 20 minutes of inactivity.

## 2. Products

The system shall allow a Store Manager to add a product with a SKU, a name, a unit price and a reorder level.
The system shall reject a product whose SKU already exists and show the message "SKU already in use".
Product images may be uploaded by the user.
The system shall display the product list sorted by name, 25 products per page.
Search shall be fast.
The system shall allow a Clerk to search products by SKU or by name.
Product prices shall be validated.
The system shall store unit prices with two decimal places.

## 3. Stock movements

The system shall record each stock movement with the product SKU, quantity, movement type, user and timestamp.
The system shall reject a stock-out movement that would make the stock level negative.
The system shall update the stock level and shall notify the Store Manager by email when the level falls below the reorder level.
Stock levels should be accurate.
The system shall allow a Store Manager to reverse a stock movement within 24 hours of recording it.
Reversed movements shall be kept and marked as reversed.
The system shall handle bulk imports of movements, TBD.
The system shall respond within an acceptable time when recording a movement.

## 4. Reports

The system shall generate a daily stock report at 23:00 Riyadh time.
The system shall export reports as CSV files.
Reports should load quickly.
The system shall allow a Store Manager to filter the movement report by date range and by product.
The system shall show the total stock value as the sum of quantity multiplied by unit price.
Charts and/or tables shall be shown on the dashboard.
The dashboard shall be intuitive.
The system shall keep movement records for at least 3 years.

## 5. Quality

The system shall return search results within 2 seconds for 95% of requests with 100 concurrent users.
The system shall be highly available.
The system shall be available 99.5% of the time each calendar month, excluding announced maintenance.
All user input shall be validated.
The system shall reject any request without a valid session token with HTTP status 401.
The system shall be easy to maintain.
The system shall write an audit log entry for every change to a product or stock level, including the user and the time.
The system shall support many concurrent users.
