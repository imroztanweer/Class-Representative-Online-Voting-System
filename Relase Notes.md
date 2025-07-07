🗳️ Online Voting System – Release Notes

Version: 1.0

Release Date: 07 July 2025

Author: Imroz Tanweer

Institution: SASTRA University

Project Title: SASTRA Class Representative Voting



✅ Summary

This release delivers the full-featured, production-ready version of the Online Voting System for Class Representative Elections with separate portals for students and admins, robust vote tracking, candidate management, visualizations, security controls, and modern UI design.



🆕 Major Features



👥 User Roles

Student Panel



Secure login with registration number and password



Dashboard showing personal details and voting status



Cast vote once per position



View ballot summary and final results



Real-time vote charts (bar graph per position)



Countdown timer to voting deadline



Responsive design + dark mode toggle



Admin Panel



Login with admin credentials



Dashboard with election summary and live stats



Manage:



Students (add, edit, auto-gen reg numbers)



Candidates (add, modify, delete with remark logging)



Voting positions (President, Secretary, etc.)



Voting deadlines and election title



View \& export all votes



Delete invalid votes with reason (audit-logged)



View detailed audit log (who changed what \& when)



Live vote charts (grouped per position)



Export votes to PDF/CSV (optional upgrade)



🎨 UI/UX Enhancements

Glassmorphism design across all pages



Responsive layout for mobile/tablet



Consistent navbar and footer



Visual highlights for vote counts and candidate bars



Chart.js integration for real-time charts



Dynamic countdown timer on student dashboard



🔐 Security \& Logic

Session-based login management



Password change support for all users



Prevents duplicate voting by timestamp lock



Audit trail for all critical admin actions



Form validation and confirmation prompts



📊 Charts \& Visualization

Student: live bar charts per position



Admin: charts grouped by position with full ballot table



Color-coded vote bars



Real-time chart refresh on page load



📁 Project Structure (Core)

plaintext

Copy

Edit

/Online Voting/

├── app.py

├── database.db

├── requirements.txt

├── static/

│   ├── style.css

│   ├── logo.png

│   └── chart.min.js

├── templates/

│   ├── base.html

│   ├── student\_base.html

│   ├── admin\_base.html

│   ├── login.html

│   ├── dashboard.html

│   ├── student\_dashboard.html

│   ├── vote.html

│   ├── results.html

│   ├── live\_vote\_count.html

│   ├── admin\_votes.html

│   ├── manage\_candidates.html

│   ├── modify\_candidate.html

│   ├── edit\_student.html

│   ├── add\_student.html

│   ├── student\_profile.html

│   ├── election\_settings.html

│   ├── audit\_log.html

│   └── header.html

🛠️ Known Issues / Future Enhancements

PDF/CSV export for admin (planned)



Password recovery (optional upgrade)



Email alerts on vote cast or admin actions



Admin impersonate student (testing mode)



👨‍💻 Designed By

Imroz Tanweer

Senior Analyst, HCLTech

For SASTRA University Project Submission

