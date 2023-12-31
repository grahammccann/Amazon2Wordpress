import base64
import json
import os
import re
import openai
import requests
import markdown2
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from PyQt5.QtWidgets import (QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
                             QWidget, QTextEdit, QTabWidget, QDesktopWidget, QTableWidget, QTableWidgetItem,
                             QMessageBox, QComboBox, QLabel, QFormLayout)

from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QMessageBox
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
        self.cache_file = "product_cache.json"
        self.product_cache = self.load_cache()

    def extract_tags_from_content(self, content):
        nltk.download('punkt')
        nltk.download('stopwords')
        stop_words = set(stopwords.words('english'))

        # Tokenize the content
        word_tokens = word_tokenize(content)

        # Remove stopwords and non-alphabetic tokens
        filtered_tokens = [w for w in word_tokens if w.isalpha() and w.lower() not in stop_words]

        # Get the frequency distribution
        freq_dist = nltk.FreqDist(filtered_tokens)

        # Get the top 10 most common words as tags
        tags = [word for word, freq in freq_dist.most_common(10)]

        return tags

    def update_generate_article_button_state(self):
        if not self.wp_html_content.toPlainText().strip():
            self.generate_article_button.setDisabled(True)
        else:
            self.generate_article_button.setDisabled(False)

    def load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as file:
                return json.load(file)
        else:
            # Create the cache file if it doesn't exist
            with open(self.cache_file, 'w') as file:
                json.dump({}, file)
        return {}

    def save_cache(self):
        with open(self.cache_file, 'w') as file:
            json.dump(self.product_cache, file, indent=4)

    def generate_article(self):
        prompt = self.article_prompt.toPlainText()

        # Extract current content from wp_html_content for context
        current_content = self.wp_html_content.toPlainText()

        # Combine the current content with the prompt to give more context
        prompt_with_context = current_content + "\n\n" + prompt

        if not prompt:
            QMessageBox.warning(self, "Missing Prompt", "Please provide a prompt for the article.")
            return
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Use GPT-4 model
                messages=[
                    {"role": "user", "content": prompt_with_context}
                ]
            )
            article_content = markdown2.markdown(response.choices[0].message.content)

            # Extract the <h1> heading from the generated content
            h1_heading = re.search(r"<h1.*?>(.*?)</h1>", article_content)
            if h1_heading:
                h1_text = h1_heading.group(1)  # Extract the text inside the <h1> tags
                self.post_title_entry.setText(h1_text)  # Set the extracted title as the post title
                article_content = article_content.replace(h1_heading.group(0),
                                                          "")  # Remove the <h1> heading from the article content
            else:
                h1_text = ""

            # Combine the <h1> heading, current content, and the rest of the article content
            organized_content = h1_text + "\n\n" + current_content + "\n\n" + article_content

            # Set the organized content back to the QTextEdit
            self.wp_html_content.setPlainText(organized_content)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def generate_ai_product_data(self, product_name):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": f"Provide 5 bullet points (in ordered list format) about the product: {product_name}"}
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
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(
            ["Product Name", "Main Image", "Price", "Reviews", "Product URL", "Bullet Points", "ASIN"])
        table_layout.addWidget(self.data_table)

        self.table_tab.setLayout(table_layout)
        self.tabs.addTab(self.table_tab, "Data Table")

        # WordPress HTML Tab
        self.wp_html_tab = QWidget()
        wp_html_layout = QVBoxLayout()

        self.template_dropdown = QComboBox(self)
        self.template_dropdown.addItems(self.templates)
        self.template_dropdown.currentIndexChanged.connect(self.template_selected)
        wp_html_layout.addWidget(self.template_dropdown)

        # Post Title
        self.post_title_label = QLabel("Post Title:", self)
        wp_html_layout.addWidget(self.post_title_label)

        self.post_title_entry = QLineEdit(self)
        self.post_title_entry.setPlaceholderText('Enter Post Title...')
        wp_html_layout.addWidget(self.post_title_entry)

        # Post Body
        self.post_body_label = QLabel("Post Body:", self)
        wp_html_layout.addWidget(self.post_body_label)

        self.wp_html_content = QTextEdit(self)
        wp_html_layout.addWidget(self.wp_html_content)

        self.generate_wp_html_button = QPushButton('Generate WordPress HTML', self)
        self.generate_wp_html_button.clicked.connect(self.generate_wp_html)
        wp_html_layout.addWidget(self.generate_wp_html_button)

        # WordPress Username
        self.wp_username_label = QLabel("WordPress Username:", self)
        wp_html_layout.addWidget(self.wp_username_label)

        self.wp_username_entry = QLineEdit(self)
        wp_html_layout.addWidget(self.wp_username_entry)

        # WordPress Password
        self.wp_password_label = QLabel("WordPress Password:", self)
        wp_html_layout.addWidget(self.wp_password_label)

        self.wp_password_entry = QLineEdit(self)
        self.wp_password_entry.setEchoMode(QLineEdit.Password)
        wp_html_layout.addWidget(self.wp_password_entry)

        # Category Dropdown
        self.category_label = QLabel("Select Category:", self)
        wp_html_layout.addWidget(self.category_label)

        self.category_dropdown = QComboBox(self)
        wp_html_layout.addWidget(self.category_dropdown)

        # WordPress Site URL
        self.wp_site_url_label = QLabel("WordPress Site URL:", self)
        wp_html_layout.addWidget(self.wp_site_url_label)

        self.wp_site_url_entry = QLineEdit(self)
        wp_html_layout.addWidget(self.wp_site_url_entry)

        # Save WordPress Credentials Button
        self.save_wp_credentials_button = QPushButton('Save WordPress Credentials', self)
        self.save_wp_credentials_button.clicked.connect(self.save_wp_credentials)
        wp_html_layout.addWidget(self.save_wp_credentials_button)

        # Amazon Affiliate ID
        self.amazon_affiliate_id_label = QLabel("Amazon Affiliate ID:", self)
        wp_html_layout.addWidget(self.amazon_affiliate_id_label)

        self.amazon_affiliate_id_entry = QLineEdit(self)
        wp_html_layout.addWidget(self.amazon_affiliate_id_entry)

        # Add Amazon Domain Dropdown
        wp_html_layout.addWidget(QLabel("Amazon Domain:"))
        self.amazon_domain_dropdown = QComboBox(self)
        self.amazon_domain_dropdown.addItems(["amazon.com", "amazon.co.uk", "amazon.ca", "amazon.com.au", "amazon.in"])
        wp_html_layout.addWidget(self.amazon_domain_dropdown)

        # Existing code
        self.show_price_checkbox = QCheckBox("Show Price", self)
        self.show_price_checkbox.setChecked(False)
        wp_html_layout.addWidget(self.show_price_checkbox)

        # Add this new checkbox
        self.show_rating_checkbox = QCheckBox("Show Rating", self)
        self.show_rating_checkbox.setChecked(False)
        wp_html_layout.addWidget(self.show_rating_checkbox)

        # Initialize the label
        self.button_text_label = QLabel("Button Text:", self)

        # Initialize the entry (assuming you're using QLineEdit)
        self.button_text_entry = QLineEdit(self)
        self.button_text_entry.setText("Check Price")

        # Add them to the layout
        wp_html_layout.addWidget(self.button_text_label)
        wp_html_layout.addWidget(self.button_text_entry)

        # Add the "Post to WordPress" button
        self.post_to_wp_button = QPushButton('Post to WordPress', self)
        self.post_to_wp_button.clicked.connect(self.post_to_wordpress)
        wp_html_layout.addWidget(self.post_to_wp_button)

        self.wp_html_tab.setLayout(wp_html_layout)
        self.tabs.addTab(self.wp_html_tab, "WordPress HTML")

        self.setCentralWidget(self.tabs)

    def post_to_wordpress(self):
        # Check if post title is empty
        if not self.post_title_entry.text().strip():
            QMessageBox.warning(self, "Missing Information", "Please provide a post title.")
            return
        try:
            api_endpoint = f"{self.wp_site_url}/wp-json/wp/v2/posts"
            headers = {
                "Authorization": f"Basic {base64.b64encode(f'{self.wp_username}:{self.wp_password}'.encode()).decode()}"
            }
            tag_names = self.extract_tags_from_content(self.wp_html_content.toPlainText())

            # Convert each tag to lowercase
            tag_names = [tag.lower() for tag in tag_names]

            tag_ids = self.get_or_create_tags(tag_names)

            data = {
                "title": self.post_title_entry.text(),
                "content": self.wp_html_content.toPlainText(),
                "status": "publish",
                "categories": [self.category_dropdown.currentData()],
                "tags": tag_ids
            }
            response = requests.post(api_endpoint, headers=headers, json=data)
            if response.status_code == 201:
                QMessageBox.information(self, "Post Successful", "Your content has been posted successfully!")
            else:
                QMessageBox.warning(self, "Post Failed", f"Failed to post content. Error: {response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def get_or_create_tags(self, tag_names):
        tag_ids = []
        for tag_name in tag_names:
            # Check if the tag exists
            response = requests.get(f"{self.wp_site_url}/wp-json/wp/v2/tags?search={tag_name}")
            if response.status_code == 200 and response.json():
                tag_ids.append(response.json()[0]['id'])
            else:
                # If tag doesn't exist, create it
                headers = {
                    "Authorization": f"Basic {base64.b64encode(f'{self.wp_username}:{self.wp_password}'.encode()).decode()}"
                }
                data = {
                    "name": tag_name
                }
                response = requests.post(f"{self.wp_site_url}/wp-json/wp/v2/tags", headers=headers, json=data)
                if response.status_code == 201:
                    tag_ids.append(response.json()['id'])
        return tag_ids

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

    def save_wp_credentials(self):
        self.wp_username = self.wp_username_entry.text()
        self.wp_password = self.wp_password_entry.text()
        self.wp_site_url = self.wp_site_url_entry.text()
        self.amazon_affiliate_id = self.amazon_affiliate_id_entry.text()
        self.amazon_domain = self.amazon_domain_dropdown.currentText()

        # Save to JSON file
        with open(self.settings_file, 'w') as file:
            json.dump({
                'wp_username': self.wp_username,
                'wp_password': self.wp_password,
                'wp_site_url': self.wp_site_url,
                'amazon_affiliate_id': self.amazon_affiliate_id,
                'amazon_domain': self.amazon_domain
            }, file, indent=4)

        QMessageBox.information(self, "Settings Saved", "Your WordPress credentials have been saved successfully!")


    def update_url_textbox(self, qurl):
        self.url_entry.setText(qurl.toString())

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
        self.current_data = {}

        product_url = self.url_entry.text()  # Get the current URL from the url_entry widget
        domain_from_settings = self.amazon_domain_dropdown.currentText()  # Get the domain from the settings dropdown

        if domain_from_settings not in product_url:
            return  # Not a product page from the selected domain, so return without extracting data

        self.prompted = False  # Reset the prompted flag

        try:
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

            # Extract ASIN number
            asin_match = re.search(r'/dp/(\w+)/', product_url)
            if asin_match:
                asin = asin_match.group(1)
                print(f"Extracted ASIN: {asin}")  # Add this line for debugging
                self.current_data['asin'] = asin

        except Exception as e:
            print(f"Error in extract_data: {e}")

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
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText("All data points found. Do you want to extract the data?")
            msg.setWindowTitle("Extract Data?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            retval = msg.exec_()
            if retval == QMessageBox.Yes:
                product_name = self.current_data['product_name']

                # Initialize product_info to None
                product_info = None

                # Check if the product name or ASIN is in the cache
                if product_name in self.product_cache:
                    # Use the bullet points from the cache
                    product_info = self.product_cache[product_name]['bullet_points']

                    # Alert with a popup that we're using already saved data
                    info_msg = QMessageBox()
                    info_msg.setIcon(QMessageBox.Information)
                    info_msg.setText("Using already saved data from cache. Not querying OpenAI.")
                    info_msg.setWindowTitle("Information")
                    info_msg.exec_()

                    # Debug print statement
                    print("Using saved description from cache.")

                else:

                    # Generate bullet points using AI
                    product_info = self.generate_ai_product_data(product_name)

                    # Debug print statement
                    print("Using AI-generated description.")

                if product_info:
                    self.result_text.append(f"[INFO] AI Generated Product Info: {product_info}")
                    # Store the AI data in current_data
                    self.current_data['product_info'] = product_info
                self.add_to_table()
        except Exception as e:
            print(f"Error in prompt_extraction: {e}")

    def template_selected(self, index):
        self.selected_template = self.templates[index]

    def add_to_table(self):
        try:
            rows = self.data_table.rowCount()
            for i in range(rows):
                if self.data_table.item(i, 0).text() == self.current_data.get('product_name', ''):
                    return  # Duplicate found, do not add

            self.data_table.insertRow(rows)
            self.data_table.setItem(rows, 0, QTableWidgetItem(str(self.current_data.get('product_name', ''))))
            self.data_table.setItem(rows, 1, QTableWidgetItem(str(self.current_data.get('main_image', ''))))
            self.data_table.setItem(rows, 2, QTableWidgetItem(str(self.current_data.get('price', ''))))
            self.data_table.setItem(rows, 3, QTableWidgetItem(str(self.current_data.get('reviews', ''))))
            self.data_table.setItem(rows, 4, QTableWidgetItem(str(self.url_entry.text())))
            self.data_table.setItem(rows, 5,
                                    QTableWidgetItem(str(self.current_data.get('product_info', ''))))  # Bullet Points
            print(f"ASIN before adding to table: {self.current_data.get('asin', 'N/A')}")  # Debugging line
            self.data_table.setItem(rows, 6, QTableWidgetItem(str(self.current_data.get('asin', ''))))  # ASIN

            # Save to JSON
            self.save_to_cache(self.current_data.get('product_name', ''), {
                'asin': self.current_data.get('asin', ''),
                'bullet_points': self.current_data.get('product_info', '')
            })

            self.generate_wp_html()

        except Exception as e:
            print(f"Error in add_to_table: {e}")

    def save_to_cache(self, product_name, data):
        # Check if the product name (or ASIN) is already in the cache
        if product_name in self.product_cache:
            return  # Skip saving if it's already in the cache

        self.product_cache[product_name] = data
        self.save_cache()

    def generate_wp_html(self):
        product_boxes_html = ""
        for i in range(self.data_table.rowCount()):
            product_name = self.data_table.item(i, 0).text()
            main_image = self.data_table.item(i, 1).text()
            price = self.data_table.item(i, 2).text()
            reviews = self.data_table.item(i, 3).text()
            product_url = self.data_table.item(i, 4).text()
            product_info = self.data_table.item(i, 5).text() if self.data_table.item(i, 5) else ''

            amazon_base_url = f"https://{self.amazon_domain_dropdown.currentText()}"
            product_path = "/".join(product_url.split("/")[3:-1])
            amazon_url = f"{amazon_base_url}/{product_path}/?tag={self.amazon_affiliate_id}"

            button_text = self.button_text_entry.text() or "View on Amazon"
            show_price = self.show_price_checkbox.isChecked()
            price_html = f'<span class="product-price">{price}</span>' if show_price else ""

            # Check the state of the show_rating_checkbox
            show_rating = self.show_rating_checkbox.isChecked()
            reviews_html = f'<span class="product-reviews">{reviews}</span>' if show_rating else ""

            ribbon_html = f'<div class="product-ribbon">#{i + 1} Best Seller</div>'

            product_boxes_html += f"""
                <div class="product-container">
                    {ribbon_html}
                    <a href="{amazon_url}" target="_blank" class="product-image-link">
                        <img src="{main_image}" alt="{product_name}" class="product-image">
                    </a>
                    <div class="product-details">
                            <h2 class="product-name">{product_name}</h2>
                        <div class="product-price-reviews">
                            {price_html}
                            {reviews_html}
                        </div>
                        <ol class="product-bullet-points">{product_info}</ol>
                        <a href="{amazon_url}" target="_blank" class="view-on-amazon"><i class="fas fa-shopping-cart"></i> {button_text}</a>
                    </div>
                </div>
            """

        self.wp_html_content.setPlainText(product_boxes_html)

        # Automatically render the WordPress HTML
        self.render_html_content()


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = BrowserApp()
    window.show()
    sys.exit(app.exec_())