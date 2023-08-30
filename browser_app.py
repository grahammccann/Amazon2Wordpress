import base64
import json
import os
import requests
from PyQt5.QtWidgets import (QMainWindow, QLineEdit, QPushButton, QVBoxLayout,
                             QWidget, QTextEdit, QTabWidget, QDesktopWidget, QTableWidget, QTableWidgetItem,
                             QMessageBox, QComboBox, QLabel, QFormLayout)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl


class BrowserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.templates = ["Comparison Tables"]
        self.selected_template = self.templates[0]
        self.current_data = {}
        self.prompted = False
        self.wp_username = ""
        self.wp_password = ""
        self.wp_site_url = ""
        self.amazon_affiliate_id = ""
        self.settings_file = "settings.json"
        self.initUI()
        self.load_settings()
        self.browser.urlChanged.connect(self.update_url_textbox)

    def initUI(self):
        self.setWindowTitle('Embedded Browser - graham23s@hotmail.com')
        self.setGeometry(100, 100, 800, 600)
        self.center()

        self.tabs = QTabWidget()

        # Browser Tab
        self.browser_tab = QWidget()
        browser_layout = QVBoxLayout()

        self.url_entry = QLineEdit(self)
        self.url_entry.setPlaceholderText('Enter Amazon Product URL...')
        browser_layout.addWidget(self.url_entry)

        self.go_button = QPushButton('Go', self)
        self.go_button.clicked.connect(self.navigate)
        browser_layout.addWidget(self.go_button)

        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36")

        self.browser = QWebEngineView(self)
        self.browser.setPage(QWebEnginePage(profile, self.browser))
        self.browser.load(QUrl('https://www.google.com'))
        self.browser.loadFinished.connect(self.fetch_html_content)
        browser_layout.addWidget(self.browser)

        self.extract_button = QPushButton('Extract Amazon Data', self)
        self.extract_button.clicked.connect(self.extract_data)
        browser_layout.addWidget(self.extract_button)

        self.browser_tab.setLayout(browser_layout)
        self.tabs.addTab(self.browser_tab, "Browser")

        # Rendered HTML Tab
        self.rendered_html_tab = QWidget()
        rendered_html_layout = QVBoxLayout()

        self.rendered_html_browser = QWebEngineView(self)
        rendered_html_layout.addWidget(self.rendered_html_browser)

        self.render_button = QPushButton('Render HTML', self)
        self.render_button.clicked.connect(self.render_html_content)
        rendered_html_layout.addWidget(self.render_button)

        self.rendered_html_tab.setLayout(rendered_html_layout)
        self.tabs.addTab(self.rendered_html_tab, "Rendered HTML")

        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.tab_changed)

        # Data Tab
        self.data_tab = QWidget()
        data_layout = QVBoxLayout()

        self.result_text = QTextEdit(self)
        data_layout.addWidget(self.result_text)

        self.data_tab.setLayout(data_layout)
        self.tabs.addTab(self.data_tab, "Extracted Data")

        # HTML Content Tab
        self.html_content_tab = QWidget()
        html_content_layout = QVBoxLayout()

        self.html_content_text = QTextEdit(self)
        html_content_layout.addWidget(self.html_content_text)

        self.html_content_tab.setLayout(html_content_layout)
        self.tabs.addTab(self.html_content_tab, "HTML Content")

        # Table Tab
        self.table_tab = QWidget()
        table_layout = QVBoxLayout()

        self.data_table = QTableWidget(self)
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["Product Name", "Main Image", "Price", "Reviews", "Product URL"])
        table_layout.addWidget(self.data_table)

        self.table_tab.setLayout(table_layout)
        self.tabs.addTab(self.table_tab, "Data Table")

        # WordPress HTML Tab
        self.wp_html_tab = QWidget()
        wp_html_layout = QVBoxLayout()

        self.post_title_entry = QLineEdit(self)
        self.post_title_entry.setPlaceholderText('Enter Post Title...')
        wp_html_layout.addWidget(self.post_title_entry)

        self.template_dropdown = QComboBox(self)
        self.template_dropdown.addItems(self.templates)
        self.template_dropdown.currentIndexChanged.connect(self.template_selected)
        wp_html_layout.addWidget(self.template_dropdown)

        self.wp_html_content = QTextEdit(self)
        wp_html_layout.addWidget(self.wp_html_content)

        # Category Dropdown
        self.category_dropdown = QComboBox(self)
        wp_html_layout.addWidget(QLabel("Select Category:"))
        wp_html_layout.addWidget(self.category_dropdown)

        # Post Button
        self.post_button = QPushButton('Post to WordPress', self)
        self.post_button.clicked.connect(self.post_to_wordpress)
        wp_html_layout.addWidget(self.post_button)

        self.wp_html_tab.setLayout(wp_html_layout)
        self.tabs.addTab(self.wp_html_tab, "WordPress HTML")

        # Settings Tab
        self.settings_tab = QWidget()
        settings_layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.wp_username_label = QLabel("WordPress Username:")
        self.wp_username_entry = QLineEdit(self)
        form_layout.addRow(self.wp_username_label, self.wp_username_entry)

        self.wp_password_label = QLabel("WordPress Password:")
        self.wp_password_entry = QLineEdit(self)
        self.wp_password_entry.setEchoMode(QLineEdit.Password)
        form_layout.addRow(self.wp_password_label, self.wp_password_entry)

        self.wp_site_url_label = QLabel("WordPress Site URL:")
        self.wp_site_url_entry = QLineEdit(self)
        form_layout.addRow(self.wp_site_url_label, self.wp_site_url_entry)

        self.amazon_affiliate_id_label = QLabel("Amazon Affiliate ID:")
        self.amazon_affiliate_id_entry = QLineEdit(self)
        form_layout.addRow(self.amazon_affiliate_id_label, self.amazon_affiliate_id_entry)

        settings_layout.addLayout(form_layout)

        self.save_settings_button = QPushButton("Save Settings", self)
        self.save_settings_button.clicked.connect(self.save_settings)
        settings_layout.addWidget(self.save_settings_button)

        self.settings_tab.setLayout(settings_layout)
        self.tabs.addTab(self.settings_tab, "Settings")

        self.setCentralWidget(self.tabs)

    def post_to_wordpress(self):
        try:
            api_endpoint = f"{self.wp_site_url}/wp-json/wp/v2/posts"
            headers = {
                "Authorization": f"Basic {base64.b64encode(f'{self.wp_username}:{self.wp_password}'.encode()).decode()}"
            }
            data = {
                "title": self.post_title_entry.text(),
                "content": self.wp_html_content.toPlainText(),
                "status": "publish",
                "categories": [self.category_dropdown.currentData()]
            }
            response = requests.post(api_endpoint, headers=headers, json=data)
            if response.status_code == 201:
                QMessageBox.information(self, "Post Successful", "Your content has been posted successfully!")
            else:
                QMessageBox.warning(self, "Post Failed", f"Failed to post content. Error: {response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def fetch_categories(self):
        api_endpoint = f"{self.wp_site_url}/wp-json/wp/v2/categories"
        response = requests.get(api_endpoint)
        if response.status_code == 200:
            categories = response.json()
            for category in categories:
                self.category_dropdown.addItem(category['name'], category['id'])
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch categories from WordPress.")

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as file:
                data = json.load(file)
                self.wp_username = data.get('wp_username', "")
                self.wp_password = data.get('wp_password', "")
                self.wp_site_url = data.get('wp_site_url', "")
                self.amazon_affiliate_id = data.get('amazon_affiliate_id', "")

            # Set the text of the UI components
            self.wp_username_entry.setText(self.wp_username)
            self.wp_password_entry.setText(self.wp_password)
            self.wp_site_url_entry.setText(self.wp_site_url)
            self.amazon_affiliate_id_entry.setText(self.amazon_affiliate_id)

            # Fetch categories after loading settings
            self.fetch_categories()

    def save_settings(self):
        self.wp_username = self.wp_username_entry.text()
        self.wp_password = self.wp_password_entry.text()
        self.wp_site_url = self.wp_site_url_entry.text()
        self.amazon_affiliate_id = self.amazon_affiliate_id_entry.text()

        # Save to JSON file
        with open(self.settings_file, 'w') as file:
            json.dump({
                'wp_username': self.wp_username,
                'wp_password': self.wp_password,
                'wp_site_url': self.wp_site_url,
                'amazon_affiliate_id': self.amazon_affiliate_id
            }, file, indent=4)

        QMessageBox.information(self, "Settings Saved", "Your settings have been saved successfully!")

    def update_url_textbox(self, qurl):
        self.url_entry.setText(qurl.toString())

    def tab_changed(self, index):
        # Check if the current tab is "Rendered HTML"
        if self.tabs.tabText(index) == "Rendered HTML":
            css_content = """
            <style>
                .a-comparison-table {
                    width: 80%; /* Adjusted width */
                    margin: 20px auto; /* Center the table */
                    border-collapse: collapse;
                    font-family: Arial, sans-serif;
                    box-shadow: 0 0 20px rgba(0,0,0,0.15);
                }
                .a-comparison-table th, .a-comparison-table td {
                    border: 1px solid #dddddd;
                    padding: 12px 15px; /* Increased padding */
                    text-align: center; /* Centered text */
                }
                .a-comparison-table th {
                    background-color: #f7f7f7;
                    color: #333;
                    font-weight: bold;
                }
                .a-comparison-table tr:nth-child(even) {
                    background-color: #f2f2f2;
                }
                .a-comparison-table tr:hover {
                    background-color: #f5f5f5;
                }
                .a-comparison-table img {
                    max-width: 100px; /* Adjust as needed */
                    border-radius: 5px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }
            </style>
            """
            html_content = css_content + self.wp_html_content.toPlainText()
            self.rendered_html_browser.setHtml(html_content)

    def render_html_content(self):
        bootstrap_cdn = '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">'
        font_awesome_cdn = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">'
        html_content = font_awesome_cdn + bootstrap_cdn + self.wp_html_content.toPlainText().strip()
        self.rendered_html_browser.setHtml(html_content)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def navigate(self):
        url = self.url_entry.text()
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        self.browser.load(QUrl(url))

    def extract_data(self):
        self.prompted = False  # Reset the prompted flag

        # Product Name
        js_product_name = """
        document.querySelector("#productTitle") ? document.querySelector("#productTitle").textContent.trim() : ""
        """
        self.browser.page().runJavaScript(js_product_name, self.store_and_check_data('product_name'))

        # Main Image
        js_main_image = """
        document.querySelector("#landingImage") ? document.querySelector("#landingImage").src : ""
        """
        self.browser.page().runJavaScript(js_main_image, self.store_and_check_data('main_image'))

        # Price
        js_price = """
        document.querySelector(".a-price .a-offscreen") ? document.querySelector(".a-price .a-offscreen").textContent.trim() :
        (document.querySelector(".a-price .a-price-whole") ? document.querySelector(".a-price .a-price-whole").textContent.trim() : "")
        """
        self.browser.page().runJavaScript(js_price, self.store_and_check_data('price'))

        # Reviews
        js_reviews = """
        document.querySelector("#acrCustomerReviewText") ? document.querySelector("#acrCustomerReviewText").textContent.trim() : ""
        """
        self.browser.page().runJavaScript(js_reviews, self.store_and_check_data('reviews'))

    def fetch_html_content(self):
        self.browser.page().toHtml(self.display_html_content)
        self.extract_data()

    def display_html_content(self, html_content):
        self.html_content_text.setPlainText(html_content)

    def store_and_check_data(self, key):
        def callback(result):
            if result:
                self.current_data[key] = result
                self.result_text.append(
                    f"[INFO] Extracted {key}: {result}")  # Display extracted data in the "Extracted Data" tab
            else:
                self.result_text.append(f"[WARNING] Failed to extract {key}")  # Display warning for missing data

            # Check if all data points are present
            required_data_points = ['product_name', 'main_image', 'price', 'reviews']
            if all(point in self.current_data for point in required_data_points) and not self.prompted:
                self.prompted = True
                self.prompt_extraction()

            # Add a newline after the last required data point is extracted
            if key == required_data_points[-1]:
                self.result_text.append("\n")

        return callback

    def prompt_extraction(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText("All data points found. Do you want to extract the data?")
        msg.setWindowTitle("Extract Data?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        retval = msg.exec_()
        if retval == QMessageBox.Yes:
            self.add_to_table()

    def template_selected(self, index):
        self.selected_template = self.templates[index]

    def add_to_table(self):
        rows = self.data_table.rowCount()
        for i in range(rows):
            if self.data_table.item(i, 0).text() == self.current_data['product_name']:
                return  # Duplicate found, do not add
        self.data_table.insertRow(rows)
        self.data_table.setItem(rows, 0, QTableWidgetItem(self.current_data['product_name']))
        self.data_table.setItem(rows, 1, QTableWidgetItem(self.current_data['main_image']))
        self.data_table.setItem(rows, 2, QTableWidgetItem(self.current_data['price']))
        self.data_table.setItem(rows, 3, QTableWidgetItem(self.current_data['reviews']))
        self.data_table.setItem(rows, 4, QTableWidgetItem(self.url_entry.text()))  # Add the product URL to the data table

        # Construct WordPress HTML based on the entire data table
        table_rows_html = ""
        for i in range(self.data_table.rowCount()):
            product_name = self.data_table.item(i, 0).text()
            main_image = self.data_table.item(i, 1).text()
            price = self.data_table.item(i, 2).text()
            reviews = self.data_table.item(i, 3).text()
            product_url = self.data_table.item(i, 4).text()  # Get the product URL from the data table

            # Construct the Amazon URL with the affiliate tag for each product
            amazon_base_url = "https://www.amazon.co.uk"
            product_path = "/".join(product_url.split("/")[3:6])  # Extracting the essential part of the URL
            affiliate_tag = f"?tag={self.amazon_affiliate_id}"
            amazon_url = amazon_base_url + "/" + product_path + "/" + affiliate_tag

            # Add a Bootstrap-styled link that looks like a button to the table with Font Awesome cart icon for each product
            amazon_link = f'<a href="{amazon_url}" class="btn btn-success" target="_blank"><i class="fas fa-shopping-cart"></i> Check Price</a>'

            table_rows_html += f"""
            <tr>
                <td><img src="{main_image}" alt="{product_name}" class="img-thumbnail" width="100"></td>
                <td>{product_name}</td>
                <td>{price}</td>
                <td>{reviews}</td>
                <td class="text-end">
                    <div class="mt-2">
                        {amazon_link}
                    </div>
                </td>
            </tr>
            """

        html_content = f"""
        <div class="table-responsive">
            <table class="table table-bordered table-striped table-hover">
                <thead>
                    <tr>
                        <th>Image</th>
                        <th>Name</th>
                        <th>Price</th>
                        <th>Reviews</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
        </div>
        """

        self.wp_html_content.setPlainText(html_content)

        # Reset the current_data dictionary to ensure it's empty for the next product
        self.current_data = {}