import base64
import json
import os
import openai
import requests
import markdown2
from PyQt5.QtWidgets import (QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
                             QWidget, QTextEdit, QTabWidget, QDesktopWidget, QTableWidget, QTableWidgetItem,
                             QMessageBox, QComboBox, QLabel, QFormLayout)

from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QCheckBox
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]

class BrowserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.callback_counter = 0
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

    def generate_ai_product_data(self, product_name):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": f"Provide 5 bullet points about the product: {product_name}"}
                ]
            )
            return markdown2.markdown(response.choices[0].message.content)
        except openai.error.OpenAIError as e:
            print(f"OpenAI API Error: {e}")
            return None

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
        self.data_table.setColumnCount(6)
        self.data_table.setHorizontalHeaderLabels(
            ["Product Name", "Main Image", "Price", "Reviews", "Product URL", "Bullet Points"])
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
        wp_html_layout.addWidget(QLabel("Select Category:"))
        self.category_dropdown = QComboBox(self)
        wp_html_layout.addWidget(self.category_dropdown)

        # Button Text Entry
        wp_html_layout.addWidget(QLabel("Button Text:"))
        self.button_text_entry = QLineEdit(self)
        self.button_text_entry.setPlaceholderText('e.g. View on Amazon')
        wp_html_layout.addWidget(self.button_text_entry)

        # Show Price Checkbox
        self.show_price_checkbox = QCheckBox("Show Price")
        self.show_price_checkbox.setChecked(True)
        wp_html_layout.addWidget(self.show_price_checkbox)

        # Post Button
        self.post_button = QPushButton('Post to WordPress', self)
        self.post_button.clicked.connect(self.post_to_wordpress)
        wp_html_layout.addWidget(self.post_button)

        self.wp_html_tab.setLayout(wp_html_layout)
        self.tabs.addTab(self.wp_html_tab, "WordPress HTML")

        # Settings Tab
        self.settings_tab = QWidget()
        settings_layout = QVBoxLayout()

        # Use QFormLayout for the settings
        form_layout = QFormLayout()

        self.amazon_domain_dropdown = QComboBox(self)
        self.amazon_domain_dropdown.addItems(["amazon.co.uk", "amazon.com", "amazon.de"])
        form_layout.addRow("Select Amazon Domain:", self.amazon_domain_dropdown)

        self.wp_username_entry = QLineEdit(self)
        form_layout.addRow("WordPress Username:", self.wp_username_entry)

        self.wp_password_entry = QLineEdit(self)
        self.wp_password_entry.setEchoMode(QLineEdit.Password)
        form_layout.addRow("WordPress Password:", self.wp_password_entry)

        self.wp_site_url_entry = QLineEdit(self)
        form_layout.addRow("WordPress Site URL:", self.wp_site_url_entry)

        self.amazon_affiliate_id_entry = QLineEdit(self)
        form_layout.addRow("Amazon Affiliate ID:", self.amazon_affiliate_id_entry)

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

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as file:
                data = json.load(file)
                self.wp_username = data.get('wp_username', "")
                self.wp_password = data.get('wp_password', "")
                self.wp_site_url = data.get('wp_site_url', "")
                self.amazon_affiliate_id = data.get('amazon_affiliate_id', "")
                self.amazon_domain = data.get('amazon_domain', "amazon.co.uk")  # Add this line

            # Set the text of the UI components
            self.wp_username_entry.setText(self.wp_username)
            self.wp_password_entry.setText(self.wp_password)
            self.wp_site_url_entry.setText(self.wp_site_url)
            self.amazon_affiliate_id_entry.setText(self.amazon_affiliate_id)
            self.amazon_domain_dropdown.setCurrentText(self.amazon_domain)  # Add this line

            # Fetch categories after loading settings
            self.fetch_categories()

    def save_settings(self):
        self.wp_username = self.wp_username_entry.text()
        self.wp_password = self.wp_password_entry.text()
        self.wp_site_url = self.wp_site_url_entry.text()
        self.amazon_affiliate_id = self.amazon_affiliate_id_entry.text()
        self.amazon_domain = self.amazon_domain_dropdown.currentText()  # Add this line

        # Save to JSON file
        with open(self.settings_file, 'w') as file:
            json.dump({
                'wp_username': self.wp_username,
                'wp_password': self.wp_password,
                'wp_site_url': self.wp_site_url,
                'amazon_affiliate_id': self.amazon_affiliate_id,
                'amazon_domain': self.amazon_domain  # Add this line
            }, file, indent=4)

        QMessageBox.information(self, "Settings Saved", "Your settings have been saved successfully!")

    def update_url_textbox(self, qurl):
        self.url_entry.setText(qurl.toString())

    def tab_changed(self, index):
        # Check if the current tab is "Rendered HTML"
        if self.tabs.tabText(index) == "Rendered HTML":
            bootstrap_cdn = '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">'
            html_content = bootstrap_cdn + self.wp_html_content.toPlainText().strip()  # Added .strip() here
            self.rendered_html_browser.setHtml(html_content)

    def render_html_content(self):
        bootstrap_cdn = '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">'
        html_content = bootstrap_cdn + self.wp_html_content.toPlainText().strip()  # Added .strip() here
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

        current_url = self.url_entry.text()
        if "amazon.co.uk" not in current_url:
            return  # Not an Amazon product page, so return without extracting data

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
            self.callback_counter += 1

            if result:
                self.current_data[key] = result
                self.result_text.append(
                    f"[INFO] Extracted {key}: {result}")  # Display extracted data in the "Extracted Data" tab
            else:
                self.result_text.append(f"[WARNING] Failed to extract {key}")  # Display warning for missing data

            # Check if all data points are present
            required_data_points = ['product_name', 'main_image', 'price', 'reviews']
            if self.callback_counter == len(required_data_points) and not self.prompted:
                self.prompted = True
                self.prompt_extraction()

                # Reset the counter for the next extraction
                self.callback_counter = 0

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
            # Generate bullet points using AI
            product_name = self.current_data['product_name']
            product_info = self.generate_ai_product_data(product_name)
            if product_info:
                self.result_text.append(f"[INFO] AI Generated Product Info: {product_info}")
                # Store the AI data in current_data
                self.current_data['product_info'] = product_info
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
        self.data_table.setItem(rows, 4, QTableWidgetItem(self.url_entry.text()))

        # Generate AI bullet points for the product
        product_info = self.generate_ai_product_data(self.current_data['product_name'])
        self.current_data['product_info'] = product_info  # Update the dictionary with the new bullet points
        bullet_points_html = product_info.replace("\n", "<br>")
        self.data_table.setItem(rows, 5, QTableWidgetItem(product_info))  # Store bullet points in the table

        # Construct WordPress HTML based on the entire data table
        product_boxes_html = ""
        for i in range(self.data_table.rowCount()):
            product_name = self.data_table.item(i, 0).text()
            main_image = self.data_table.item(i, 1).text()
            price = self.data_table.item(i, 2).text()
            reviews = self.data_table.item(i, 3).text()
            product_url = self.data_table.item(i, 4).text()
            product_info = self.data_table.item(i, 5).text() if self.data_table.item(i, 5) else ''

            amazon_base_url = f"https://{self.amazon_domain}"
            product_path = "/".join(product_url.split("/")[3:-1])
            amazon_url = f"{amazon_base_url}/{product_path}/?tag={self.amazon_affiliate_id}"

            button_text = self.button_text_entry.text() or "View on Amazon"
            show_price = self.show_price_checkbox.isChecked()
            price_html = f'<span class="product-price">{price}</span>' if show_price else ""

            product_boxes_html += f"""
                <div class="product-container">
                    <img src="{main_image}" alt="{product_name}" class="product-image">
                    <div class="product-details">
                        <h2 class="product-name">{product_name}</h2>
                        <div class="product-price-reviews">
                            {price_html}
                            <span class="product-reviews">{reviews}</span>
                        </div>
                        <ul class="product-bullet-points">{bullet_points_html}</ul>
                        <a href="{amazon_url}" target="_blank" class="view-on-amazon"><i class="fas fa-shopping-cart"></i> {button_text}</a>
                    </div>
                </div>
            """

        wp_html = f"""
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css">
            <style>
                .product-container {{
                    width: 80%; 
                    max-width: 600px; 
                    border: 1px solid #ddd;
                    padding: 20px; 
                    font-family: Arial, sans-serif;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    margin: 20px auto; 
                }}
                .product-image {{
                    width: 100%;
                    height: auto;
                    display: block;
                    margin-bottom: 20px; 
                }}
                .product-name {{
                    font-size: 20px; 
                    font-weight: bold;
                    margin-bottom: 15px; 
                }}
                .product-price-reviews {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .product-price {{
                    color: #B12704;
                    font-size: 18px; 
                    margin-right: 10px; 
                }}
                .product-reviews {{
                    font-size: 16px; 
                }}
                .product-bullet-points {{
                    list-style-type: disc;
                    padding-left: 30px; 
                    font-size: 16px; 
                    margin-bottom: 20px; 
                }}
                .view-on-amazon {{
                    display: block;
                    width: 100%;
                    padding: 12px; 
                    background-color: #FEBD69;
                    text-align: center;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    font-size: 18px; 
                }}
                .view-on-amazon:hover {{
                    background-color: #f5a623;
                }}
                .view-on-amazon i {{
                    margin-right: 8px; 
                }}
            </style>
            {product_boxes_html}
        """

        self.wp_html_content.setPlainText(wp_html)


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = BrowserApp()
    window.show()
    sys.exit(app.exec_())