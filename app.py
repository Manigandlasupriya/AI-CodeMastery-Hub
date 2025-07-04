import json
import random
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

# Initialize Flask App
app = Flask(__name__)

# --- Configuration ---
app.config['SECRET_KEY'] = 'da2a6a0b4346309177dfbfd7af7cacb8772ac9e50c683036' # !!! IMPORTANT: Change this !!!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_app.db' # SQLite database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Disable tracking modifications for performance

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to 'login' route if user is not logged in

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True) # One-to-many relationship

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_language = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Float, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    time_taken_seconds = db.Column(db.Integer)
    date_attempted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Store wrong answers as JSON string
    wrong_answers_details = db.Column(db.Text) # JSON string of list of dicts

    def __repr__(self):
        return f'<QuizAttempt {self.id} - User {self.user_id} - {self.quiz_language} - {self.score}%>'

# --- Flask-Login user loader ---
@login_manager.user_loader
def load_user(user_id):
    # This function reloads the user object from the user ID stored in the session
    return db.session.get(User, int(user_id))

# --- Dummy Quiz Questions Data ---
quiz_questions = {
    'python': [
        {'id': 'py_q0', 'question': 'Which keyword is used to define a function in Python?', 'options': ['func', 'define', 'def', 'function'], 'correct_answer': 'def', 'explanation': 'The `def` keyword is used to define a function in Python.\nFor example: `def my_function():`.', 'topics': ['Functions', 'Syntax Basics']},
        {'id': 'py_q1', 'question': 'What is the output of `print(type([]))`?', 'options': ['<class \'list\'>', '<class \'tuple\'>', '<class \'dict\'>', '<class \'array\'>'], 'correct_answer': '<class \'list\'>', 'explanation': '`[]` denotes an empty list literal, and `type()` returns the type of the object, which is `list`.', 'topics': ['Data Structures', 'Lists', 'Built-in Functions']},
        {'id': 'py_q2', 'question': 'How do you comment out a single line in Python?', 'options': ['// This is a comment', '/* This is a comment */', '# This is a comment', '-- This is a comment'], 'correct_answer': '# This is a comment', 'explanation': 'In Python, the `#` symbol is used for single-line comments.\nFor multi-line comments, you can use triple quotes (`"""Docstring"""` or `\'\'\'Comment\'\'\'`).', 'topics': ['Syntax Basics', 'Comments']},
        {'id': 'py_q3', 'question': 'Which of these is used for iteration over a sequence (e.g. list, tuple, string) or other iterable objects?', 'options': ['for loop', 'while loop', 'do-while loop', 'if-else statement'], 'correct_answer': 'for loop', 'explanation': 'The `for` loop in Python is used to iterate over sequences or other iterable objects.', 'topics': ['Control Flow', 'Loops']},
        {'id': 'py_q4', 'question': 'What does `len("hello")` return?', 'options': ['4', '5', '6', 'Error'], 'correct_answer': '5', 'explanation': 'The `len()` function returns the number of items in an object, which is 5 for "hello".', 'topics': ['Built-in Functions', 'Strings']},
        {'id': 'py_q5', 'question': 'Which operator is used for exponentiation in Python?', 'options': ['^', '**', '*', '//'], 'correct_answer': '**', 'explanation': 'The `**` operator is used to perform exponentiation (e.g., `2 ** 3` is 8).', 'topics': ['Operators']},
        {'id': 'py_q6', 'question': 'Which of the following is an immutable data type?', 'options': ['list', 'dictionary', 'set', 'tuple'], 'correct_answer': 'tuple', 'explanation': 'Tuples are immutable;\ntheir elements cannot be changed after creation. Lists, dictionaries, and sets are mutable.', 'topics': ['Data Types', 'Immutability']},
        {'id': 'py_q7', 'question': 'What is the purpose of the `if __name__ == "__main__":` block?', 'options': ['To define a main function.', 'To make code run only when the script is executed directly.', 'To import modules.', 'To create a class.'], 'correct_answer': 'To make code run only when the script is executed directly.', 'topics': ['Modules', 'Script Execution']},
        {'id': 'py_q8', 'question': 'How do you add an element to a list in Python?', 'options': ['list.add(element)', 'list.insert(element)', 'list.append(element)', 'list.put(element)'], 'correct_answer': 'list.append(element)', 'explanation': 'The `append()` method adds an element to the end of a list.', 'topics': ['Data Structures', 'Lists']},
        {'id': 'py_q9', 'question': 'What is the correct way to open a file named "data.txt" for reading?', 'options': ['open("data.txt", "r")', 'open("data.txt", "read")', 'read("data.txt")', 'file.open("data.txt")'], 'correct_answer': 'open("data.txt", "r")', 'explanation': 'The `open()` function is used with "r" mode for reading text files.', 'topics': ['File I/O']},
        {'id': 'py_q10', 'question': 'Which module is commonly used for regular expressions in Python?', 'options': ['regex', 're', 'regexp', 'pattern'], 'correct_answer': 're', 'explanation': 'The `re` module provides regular expression operations in Python.', 'topics': ['Modules', 'Regular Expressions']},
        {'id': 'py_q11', 'question': 'What is a "docstring" in Python?', 'options': ['A single-line comment.', 'A string literal specified in source code that is used to document a specific segment of code.', 'A type of error message.', 'A variable name.'], 'correct_answer': 'A string literal specified in source code that is used to document a specific segment of code.', 'topics': ['Documentation', 'Syntax Basics']},
        {'id': 'py_q12', 'question': 'Which of the following is a correct way to create an empty dictionary?', 'options': ['{}', 'dict()', 'both {} and dict()', '[]'], 'correct_answer': 'both {} and dict()', 'explanation': 'Both `{}` and `dict()` can be used to create an empty dictionary.', 'topics': ['Data Structures', 'Dictionaries']},
        {'id': 'py_q13', 'question': 'What is the purpose of `pip` in Python?', 'options': ['A code editor.', 'A package installer for Python.', 'A debugger.', 'A web framework.'], 'correct_answer': 'A package installer for Python.', 'explanation': '`pip` is the standard package manager for Python, used to install and manage software packages (libraries) written in Python.', 'topics': ['Package Management', 'Tools']},
        {'id': 'py_q14', 'question': 'How do you handle exceptions in Python?', 'options': ['catch-throw', 'try-catch', 'try-except', 'error-handle'], 'correct_answer': 'try-except', 'explanation': 'Python uses the `try` and `except` blocks to handle exceptions.', 'topics': ['Error Handling', 'Exceptions']},
        {'id': 'py_q15', 'question': 'Which data type represents true/false values?', 'options': ['int', 'str', 'bool', 'float'], 'correct_answer': 'bool', 'explanation': 'The `bool` (Boolean) data type represents truth values: `True` or `False`.', 'topics': ['Data Types']},
        {'id': 'py_q16', 'question': 'What will `x` be after `x = 10;\nx += 5`?', 'options': ['5', '10', '15', 'Error'], 'correct_answer': '15', 'explanation': '`x += 5` is a shorthand for `x = x + 5`.\nSo, `10 + 5` equals 15.', 'topics': ['Operators', 'Variables']},
        {'id': 'py_q17', 'question': 'Which function is used to get user input in Python?', 'options': ['get_input()', 'read()', 'input()', 'console.read()'], 'correct_answer': 'input()', 'explanation': 'The `input()` function reads a line from input, converts it to a string, and returns it.', 'topics': ['Input/Output', 'Built-in Functions']},
        {'id': 'py_q18', 'question': 'What is the result of `2 * "abc"`?', 'options': ['"abcabc"', '"abc2"', 'Error', '6'], 'correct_answer': '"abcabc"', 'explanation': 'Multiplying a string by an integer N results in the string being repeated N times.', 'topics': ['Strings', 'Operators']},
        {'id': 'py_q19', 'question': 'Which concept refers to the ability of an object to take on many forms?', 'options': ['Inheritance', 'Encapsulation', 'Polymorphism', 'Abstraction'], 'correct_answer': 'Polymorphism', 'explanation': 'Polymorphism allows objects of different classes to be treated as objects of a common superclass, enabling single interfaces for different data types.', 'topics': ['OOP', 'Polymorphism']}
    ],
    'java': [
        {'id': 'java_q0', 'question': 'Which keyword is used to define a class in Java?', 'options': ['func', 'define', 'def', 'class'], 'correct_answer': 'class', 'explanation': 'The `class` keyword is used to declare a class in Java.', 'topics': ['OOP', 'Classes', 'Keywords']},
        {'id': 'java_q1', 'question': 'What is the entry point method for a Java application?', 'options': ['main()', 'start()', 'run()', 'public static void main(String[] args)'], 'correct_answer': 'public static void main(String[] args)', 'explanation': 'The `public static void main(String[] args)` method is the standard entry point for Java applications.\nIt must have this exact signature.', 'topics': ['Java Basics', 'Methods']},
        {'id': 'java_q2', 'question': 'Which of the following is a primitive data type in Java?', 'options': ['String', 'Integer', 'int', 'ArrayList'], 'correct_answer': 'int', 'explanation': '`int` is a primitive data type, while `String`, `Integer`, and `ArrayList` are reference types (objects).', 'topics': ['Data Types', 'Primitives']},
        {'id': 'java_q3', 'question': 'Which keyword is used to implement an interface in Java?', 'options': ['extends', 'implements', 'uses', 'inherits'], 'correct_answer': 'implements', 'explanation': 'The `implements` keyword is used by a class to implement an interface.', 'topics': ['OOP', 'Interfaces', 'Keywords']},
        {'id': 'java_q4', 'question': 'What is the superclass of all classes in Java?', 'options': ['Main', 'Class', 'Object', 'Root'], 'correct_answer': 'Object', 'explanation': '`java.lang.Object` is the root of the class hierarchy.\nEvery class has `Object` as a superclass.', 'topics': ['OOP', 'Inheritance']},
        {'id': 'java_q5', 'question': 'Which access modifier means the member is visible only within the class itself?', 'options': ['public', 'protected', 'private', 'default'], 'correct_answer': 'private', 'explanation': '`private` members are only accessible from within the class in which they are declared.', 'topics': ['Access Modifiers', 'Encapsulation']},
        {'id': 'java_q6', 'question': 'What will be the result of `10 / 3` in Java (integer division)?', 'options': ['3.33', '3', '4', 'Error'], 'correct_answer': '3', 'explanation': 'In Java, when both operands of the division operator (`/`) are integers, the result is also an integer (truncating any fractional part).', 'topics': ['Operators', 'Data Types']},
        {'id': 'java_q7', 'question': 'Which collection allows duplicate elements and maintains insertion order?', 'options': ['Set', 'List', 'Map', 'Queue'], 'correct_answer': 'List', 'explanation': '`List` (e.g., `ArrayList`, `LinkedList`) allows duplicate elements and maintains the order in which elements are inserted.', 'topics': ['Collections', 'Data Structures']},
        {'id': 'java_q8', 'question': 'Which keyword is used to prevent a class from being subclassed?', 'options': ['static', 'abstract', 'final', 'const'], 'correct_answer': 'final', 'explanation': 'A `final` class cannot be extended (subclassed).\nA `final` method cannot be overridden. A `final` variable cannot be reassigned.', 'topics': ['Keywords', 'OOP']},
        {'id': 'java_q9', 'question': 'What is autoboxing in Java?', 'options': ['Converting a primitive type to its corresponding wrapper class automatically.', 'Converting a wrapper class to its corresponding primitive type automatically.', 'Both of the above.', 'Neither of the above.'], 'correct_answer': 'Converting a primitive type to its corresponding wrapper class automatically.', 'explanation': 'Autoboxing is the automatic conversion that the Java compiler makes between the primitive types and their corresponding object wrapper classes.', 'topics': ['Data Types', 'Wrapper Classes']},
        {'id': 'java_q10', 'question': 'Which statement is true about Java interfaces?', 'options': ['Interfaces can have constructors.', 'Interfaces can have abstract methods only.', 'Interfaces can contain static and default methods since Java 8.', 'A class can implement only one interface.'], 'correct_answer': 'Interfaces can contain static and default methods since Java 8.', 'explanation': 'Prior to Java 8, interfaces could only have abstract methods.\nJava 8 introduced `default` and `static` methods in interfaces.', 'topics': ['OOP', 'Interfaces']},
        {'id': 'java_q11', 'question': 'Which of the following is NOT an access modifier in Java?', 'options': ['public', 'private', 'protected', 'friendly'], 'correct_answer': 'friendly', 'explanation': '`public`, `private`, and `protected` are explicit access modifiers.\nThe "default" access level is also known as package-private, but not "friendly".', 'topics': ['Access Modifiers']},
        {'id': 'java_q12', 'question': 'What is the purpose of `finally` block in try-catch-finally?', 'options': ['It executes only if an exception occurs.', 'It executes only if no exception occurs.', 'It always executes regardless of whether an exception occurred or not.', 'It is optional and rarely used.'], 'correct_answer': 'It always executes regardless of whether an exception occurred or not.', 'topics': ['Exception Handling']},
        {'id': 'java_q13', 'question': 'Which operator is used to check for equality of reference (same object) in Java?', 'options': ['==', '.equals()', '.compare()', '!='], 'correct_answer': '==', 'explanation': 'The `==` operator compares object references (memory addresses).\nThe `.equals()` method compares the actual content of objects.', 'topics': ['Operators', 'Objects']},
        {'id': 'java_q14', 'question': 'What is JVM stand for?', 'options': ['Java Virtual Machine', 'Java Visual Manager', 'Java Verified Module', 'Joint Virtual Method'], 'correct_answer': 'Java Virtual Machine', 'explanation': 'JVM is an abstract machine that provides a runtime environment for Java bytecode.\nIt is the engine that drives the Java code.', 'topics': ['JVM', 'Architecture']},
        {'id': 'java_q15', 'question': 'Which exception is thrown when an array is accessed with an illegal index?', 'options': ['IOException', 'NullPointerException', 'ArrayIndexOutOfBoundsException', 'IllegalArgumentException'], 'correct_answer': 'ArrayIndexOutOfBoundsException', 'explanation': '`ArrayIndexOutOfBoundsException` is thrown when an attempt is made to access an array with an index that is either negative or greater than or equal to the size of the array.', 'topics': ['Exceptions', 'Arrays']},
        {'id': 'java_q16', 'question': 'Which of the following creates a new thread?', 'options': ['new Thread()', 'Thread.start()', 'Thread.run()', 'Runnable.start()'], 'correct_answer': 'new Thread()', 'explanation': '`new Thread()` creates a thread object.\n`start()` is then called on the thread object to begin its execution.', 'topics': ['Concurrency', 'Threads']},
        {'id': 'java_q17', 'question': 'What is method overloading?', 'options': ['Defining multiple methods with the same name but different parameters in the same class.', 'Defining methods with the same name in different classes.', 'Overriding a method from a superclass.', 'Calling a method recursively.'], 'correct_answer': 'Defining multiple methods with the same name but different parameters in the same class.', 'explanation': 'Method overloading allows a class to have multiple methods with the same name as long as their parameter lists are different (different number of parameters, different types, or different order of types).', 'topics': ['OOP', 'Methods']},
        {'id': 'java_q18', 'question': 'Which of these is used for garbage collection in Java?', 'options': ['delete', 'remove', 'System.gc()', 'Manual memory management'], 'correct_answer': 'System.gc()', 'explanation': '`System.gc()` is a hint to the JVM to perform garbage collection, but it\'s not guaranteed to run immediately.\nJava handles memory management automatically via its garbage collector.', 'topics': ['Memory Management', 'JVM']},
        {'id': 'java_q19', 'question': 'What is the default value of a local variable in Java?', 'options': ['null', '0', 'false', 'No default value (must be initialized)'], 'correct_answer': 'No default value (must be initialized)', 'explanation': 'Local variables in Java do not have default values and must be explicitly initialized before use, otherwise, a compile-time error will occur.', 'topics': ['Variables', 'Memory']}
    ],
    'html_css': [
        {'id': 'html_q0', 'question': 'What does HTML stand for?', 'options': ['Hyper Text Markup Language', 'High Tech Modern Language', 'Hyperlink and Text Markup Language', 'Home Tool Markup Language'], 'correct_answer': 'Hyper Text Markup Language', 'explanation': 'HTML is the standard markup language for documents designed to be displayed in a web browser.', 'topics': ['HTML Basics', 'Web Fundamentals']},
        {'id': 'html_q1', 'question': 'Which HTML tag is used to define an internal style sheet?', 'options': ['<script>', '<style>', '<css>', '<link>'], 'correct_answer': '<style>', 'explanation': 'The `<style>` tag is used to define style information (CSS) for a document.', 'topics': ['HTML', 'CSS']},
        {'id': 'html_q2', 'question': 'Which CSS property controls the text size?', 'options': ['text-style', 'font-size', 'text-size', 'font-style'], 'correct_answer': 'font-size', 'explanation': 'The `font-size` property sets the size of the text.', 'topics': ['CSS Basics', 'Text Styling']},
        {'id': 'html_q3', 'question': 'What is the correct HTML for referring to an external style sheet?', 'options': ['<stylesheet>mystyle.css</stylesheet>', '<link rel="stylesheet" type="text/css" href="mystyle.css">', '<style src="mystyle.css">', '<css>mystyle.css</css>'], 'correct_answer': '<link rel="stylesheet" type="text/css" href="mystyle.css">', 'explanation': 'The `<link>` tag is used to link to external style sheets.', 'topics': ['HTML', 'CSS Linking']},
        {'id': 'html_q4', 'question': 'Which HTML element is used to specify a footer for a document or section?', 'options': ['<bottom>', '<footer>', '<end>', '<section bottom>'], 'correct_answer': '<footer>', 'explanation': 'The `<footer>` element represents a footer for its nearest sectioning content or sectioning root element.', 'topics': ['HTML5', 'Semantic HTML']},
        {'id': 'html_q5', 'question': 'How do you select an element with id "demo" in CSS?', 'options': ['.demo', '#demo', '*demo', 'element.demo'], 'correct_answer': '#demo', 'explanation': 'The `#` symbol is used to select an HTML element by its `id` attribute.', 'topics': ['CSS Selectors']},
        {'id': 'html_q6', 'question': 'Which property is used to change the background color?', 'options': ['color', 'bgcolor', 'background-color', 'background'], 'correct_answer': 'background-color', 'explanation': 'The `background-color` property sets the background color of an element.', 'topics': ['CSS', 'Styling']},
        {'id': 'html_q7', 'question': 'Which HTML tag is used to create an unordered list?', 'options': ['<ol>', '<ul>', '<list>', '<dl>'], 'correct_answer': '<ul>', 'explanation': 'The `<ul>` tag defines an unordered (bulleted) list.', 'topics': ['HTML', 'Lists']},
        {'id': 'html_q8', 'question': 'What is the purpose of the `alt` attribute in an `<img>` tag?', 'options': ['To define the image alignment.', 'To provide alternative text for an image if it cannot be displayed.', 'To specify the image source.', 'To set the image width.'], 'correct_answer': 'To provide alternative text for an image if it cannot be displayed.', 'explanation': 'The `alt` attribute specifies an alternate text for an image, if the image cannot be displayed.', 'topics': ['HTML', 'Accessibility']},
        {'id': 'html_q9', 'question': 'Which CSS property is used to add space between the element\'s border and its content?', 'options': ['margin', 'spacing', 'padding', 'border-spacing'], 'correct_answer': 'padding', 'explanation': '`padding` is the space between the content of an element and its border.\n`margin` is the space outside the border.', 'topics': ['CSS Box Model']},
        {'id': 'html_q10', 'question': 'How do you make the text bold in HTML?', 'options': ['<bold>', '<strong>', '<bld>', '<emphasis>'], 'correct_answer': '<strong>', 'explanation': 'While `<b>` also makes text bold, `<strong>` is semantically preferred as it indicates strong importance.', 'topics': ['HTML Basics', 'Text Formatting']},
        {'id': 'html_q11', 'question': 'Which CSS property is used to control the flow of text around floating elements?', 'options': ['float', 'overflow', 'clear', 'position'], 'correct_answer': 'clear', 'explanation': 'The `clear` property specifies what should happen with the element that is next to a floating element.', 'topics': ['CSS Layout', 'Floats']},
        {'id': 'html_q12', 'question': 'What is the correct HTML for a hyperlink?', 'options': ['<a name="url">Link</a>', '<href="url">Link</a>', '<a href="url">Link</a>', '<link url="url">Link</link>'], 'correct_answer': '<a href="url">Link</a>', 'explanation': 'The `<a>` tag defines a hyperlink, and its `href` attribute specifies the URL of the page the link goes to.', 'topics': ['HTML', 'Links']},
        {'id': 'html_q13', 'question': 'Which CSS property is used to make text italic?', 'options': ['font-style', 'text-italic', 'italicize', 'style-text'], 'correct_answer': 'font-style', 'explanation': 'The `font-style` property is used to set the font style to normal, italic, or oblique.', 'topics': ['CSS', 'Text Styling']},
        {'id': 'html_q14', 'question': 'Which HTML element is used for the largest heading?', 'options': ['<h6>', '<heading>', '<head>', '<h1>'], 'correct_answer': '<h1>', 'explanation': 'HTML headings are defined with the `<h1>` to `<h6>` tags.\n`<h1>` defines the most important heading.', 'topics': ['HTML Basics', 'Headings']},
        {'id': 'html_q15', 'question': 'How can you apply a style to elements with a specific class "my-class"?', 'options': ['.my-class', '#my-class', '.my-class', '<my-class>'], 'correct_answer': '.my-class', 'explanation': 'The `.` (dot) character is used in CSS to select elements by their class name.', 'topics': ['CSS Selectors']},
        {'id': 'html_q16', 'question': 'Which of the following is NOT a valid CSS unit for length?', 'options': ['px', 'em', '%', 'pt'], 'correct_answer': 'pt', 'explanation': 'While `pt` (points) is a valid CSS unit, it\'s typically used for print.\n`px`, `em`, and `%` are very common for web layouts. The question might imply relative vs absolute.\nAll are technically valid, but `pt` is least common in modern responsive web design vs `rem` or `vw/vh`.\nHowever, if the intention is to find a truly *invalid* unit, this question needs clarification.\nAssuming the intent is "least common/best practice for screens", or if one of these was genuinely invalid, let\'s pick `pt` as an example of one less frequently used in modern responsive web design compared to others for dynamic sizing.', 'topics': ['CSS Units'], 'note': 'This question might be tricky depending on strictness.\nAll are technically valid. If the context is "most common for modern web", pt is least used.'},
        {'id': 'html_q17', 'question': 'What is the purpose of the `<div>` tag?', 'options': ['To define a section of navigation links.', 'To create a line break.', 'To group block-level elements for styling or scripting.', 'To define a table row.'], 'correct_answer': 'To group block-level elements for styling or scripting.', 'explanation': 'The `<div>` tag is a generic container for flow content, which does not inherently represent anything.\nIt\'s commonly used to group elements for styling with CSS or manipulating with JavaScript.', 'topics': ['HTML Basics', 'Layout']},
        {'id': 'html_q18', 'question': 'In CSS, what is the box model property that adds space *inside* an element\'s border?', 'options': ['margin', 'border', 'padding', 'spacing'], 'correct_answer': 'padding', 'explanation': 'Padding is the space between an element\'s content and its border.\nMargin is the space outside the border. Border is the line itself.', 'topics': ['CSS Box Model']},
        {'id': 'html_q19', 'question': 'Which HTML tag is used to embed video content?', 'options': ['<media>', '<movie>', '<video>', '<play>'], 'correct_answer': '<video>', 'explanation': 'The `<video>` tag is used to embed video content in an HTML document.', 'topics': ['HTML5', 'Media']}
    ],
    'c_language': [
        {'id': 'c_q0', 'question': 'Which header file is essential for input/output operations in C?', 'options': ['<string.h>', '<stdlib.h>', '<math.h>', '<stdio.h>'], 'correct_answer': '<stdio.h>', 'explanation': 'The `<stdio.h>` header file provides standard input/output functions like `printf()` and `scanf()`.', 'topics': ['C Basics', 'File I/O', 'Headers']},
        {'id': 'c_q1', 'question': 'Which of the following is NOT a valid C data type?', 'options': ['int', 'float', 'boolean', 'char'], 'correct_answer': 'boolean', 'explanation': 'C does not have a built-in `boolean` data type.\nBoolean values are typically represented using `int` (0 for false, non-zero for true).', 'topics': ['C Basics', 'Data Types']},
        {'id': 'c_q2', 'question': 'What is the correct way to declare an integer variable `x` and initialize it to 10 in C?', 'options': ['int x = 10;', 'x = 10;', 'integer x = 10;', 'declare int x = 10;'], 'correct_answer': 'int x = 10;', 'explanation': 'In C, you must specify the data type when declaring a variable.', 'topics': ['C Basics', 'Variables']},
        {'id': 'c_q3', 'question': 'Which operator is used to get the address of a variable in C?', 'options': ['*', '&', '#', '@'], 'correct_answer': '&', 'explanation': 'The `&` (address-of) operator is used to obtain the memory address of a variable.', 'topics': ['Pointers', 'Operators']},
        {'id': 'c_q4', 'question': 'Which function is used to dynamically allocate memory in C?', 'options': ['alloc()', 'new()', 'malloc()', 'create_mem()'], 'correct_answer': 'malloc()', 'explanation': '`malloc()` (memory allocation) is a standard library function in C used to dynamically allocate a specified number of bytes of memory.', 'topics': ['Memory Management', 'Pointers']},
        {'id': 'c_q5', 'question': 'What is the purpose of the `break` statement in a `switch` statement?', 'options': ['To exit the program.', 'To skip the current iteration of a loop.', 'To terminate the `switch` statement and continue execution after it.', 'To restart the `switch` statement.'], 'correct_answer': 'To terminate the `switch` statement and continue execution after it.', 'explanation': 'The `break` statement is used to exit a `switch` statement once a matching case is found, preventing "fall-through" to subsequent cases.', 'topics': ['Control Flow', 'Switch']},
        {'id': 'c_q6', 'question': 'Which loop construct always executes its body at least once?', 'options': ['for loop', 'while loop', 'do-while loop', 'if loop'], 'correct_answer': 'do-while loop', 'explanation': 'The `do-while` loop checks the condition at the end of the loop, ensuring the loop body executes at least once.', 'topics': ['Control Flow', 'Loops']},
        {'id': 'c_q7', 'question': 'What does `NULL` represent in C?', 'options': ['An empty string.', 'A character with ASCII value 0.', 'A pointer that points to nothing.', 'An integer value of 0.'], 'correct_answer': 'A pointer that points to nothing.', 'explanation': '`NULL` is a macro constant that represents a null pointer value, indicating that a pointer does not point to any valid memory location.', 'topics': ['Pointers', 'Memory']},
        {'id': 'c_q8', 'question': 'Which keyword is used to define a constant in C?', 'options': ['const', 'final', 'static', 'fixed'], 'correct_answer': 'const', 'explanation': 'The `const` keyword is used to declare a variable as constant, meaning its value cannot be changed after initialization.', 'topics': ['Variables', 'Keywords']},
        {'id': 'c_q9', 'question': 'What is the output of `sizeof(int)` on most 64-bit systems?', 'options': ['1 byte', '2 bytes', '4 bytes', '8 bytes'], 'correct_answer': '4 bytes', 'explanation': 'The size of `int` is typically 4 bytes on most modern systems, though it is implementation-defined.', 'topics': ['Data Types', 'Memory']},
        {'id': 'c_q10', 'question': 'Which of these is the correct way to comment out multiple lines in C?', 'options': ['// This is a comment', '/* This is a multi-line comment */', '# This is a comment', ''], 'correct_answer': '/* This is a multi-line comment */', 'explanation': 'Multi-line comments in C are enclosed within `/*` and `*/`.\nSingle-line comments use `//`.', 'topics': ['C Basics', 'Comments']},
        {'id': 'c_q11', 'question': 'What is the purpose of `void` in C?', 'options': ['To indicate a function returns nothing.', 'To indicate a function takes no arguments.', 'To declare a generic pointer.', 'All of the above.'], 'correct_answer': 'All of the above.', 'explanation': '`void` can be used to specify that a function returns no value, takes no arguments, or to declare a generic pointer (`void *`).', 'topics': ['Functions', 'Pointers']},
        {'id': 'c_q12', 'question': 'Which storage class specifies that a variable has a local scope and its lifetime is throughout the program execution?', 'options': ['auto', 'register', 'static', 'extern'], 'correct_answer': 'static', 'explanation': 'A `static` local variable retains its value between function calls.\nIts lifetime is the entire program duration, but its scope is limited to the function.', 'topics': ['Storage Classes', 'Variables']},
        {'id': 'c_q13', 'question': 'How do you read a single character from the console in C?', 'options': ['scanf("%c", &ch);', 'getchar();', 'fgetc(stdin);', 'All of the above (with appropriate usage).'], 'correct_answer': 'All of the above (with appropriate usage).', 'explanation': '`scanf("%c", &ch);`, `getchar();`, and `fgetc(stdin);` are all valid ways to read a single character.\n`getchar()` is equivalent to `fgetc(stdin)`.', 'topics': ['Input/Output']},
        {'id': 'c_q14', 'question': 'What is the primary purpose of a `struct` in C?', 'options': ['To define a new data type.', 'To group variables of different data types under a single name.', 'To create a linked list.', 'To define a function signature.'], 'correct_answer': 'To group variables of different data types under a single name.', 'explanation': 'A `struct` (structure) allows you to combine variables of different data types into a single unit.', 'topics': ['Data Structures']},
        {'id': 'c_q15', 'question': 'Which standard library function is used to compare two strings in C?', 'options': ['str_compare()', 'compare_str()', 'strcmp()', 'str_equals()'], 'correct_answer': 'strcmp()', 'explanation': 'The `strcmp()` function (from `<string.h>`) compares two strings lexicographically.', 'topics': ['Strings', 'Standard Library']},
        {'id': 'c_q16', 'question': 'What is the default value of a global (external) variable in C if not initialized explicitly?', 'options': ['Garbage value', '0', 'NULL', 'Undefined'], 'correct_answer': '0', 'explanation': 'Global and static variables are automatically initialized to zero if not explicitly initialized by the programmer.', 'topics': ['Variables', 'Memory']},
        {'id': 'c_q17', 'question': 'Which of the following is a logical OR operator in C?', 'options': ['|', '&&', '||', '!'], 'correct_answer': '||', 'explanation': '`||` is the logical OR operator.\n`&&` is logical AND, `!` is logical NOT, and `|` is bitwise OR.', 'topics': ['Operators']},
        {'id': 'c_q18', 'question': 'What is the correct way to allocate memory for 5 integers using `malloc`?', 'options': ['int *arr = (int *)malloc(5);', 'int *arr = (int *)malloc(5 * sizeof(int));', 'int *arr = malloc(5, sizeof(int));', 'int *arr = new int[5];'], 'correct_answer': 'int *arr = (int *)malloc(5 * sizeof(int));', 'explanation': '`malloc` takes the size in bytes. So, for 5 integers, you multiply 5 by the size of an integer (`sizeof(int)`). The cast `(int *)` is good practice though not strictly required in C.', 'topics': ['Memory Management', 'Pointers']},
        {'id': 'c_q19', 'question': 'What is the output of `printf("%d", 5 / 2);` in C?', 'options': ['2.5', '2', '3', 'Error'], 'correct_answer': '2', 'explanation': 'In C, integer division (`/` when both operands are integers) truncates the decimal part, resulting in 2.', 'topics': ['Operators', 'Data Types']}
    ]
}

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_attempts = QuizAttempt.query.filter_by(user_id=current_user.id).order_by(QuizAttempt.date_attempted.desc()).all()

    language_stats = {}
    for lang in quiz_questions.keys():
        attempts_for_lang = [a for a in user_attempts if a.quiz_language == lang]
        if attempts_for_lang:
            highest_score = max(attempts_for_lang, key=lambda x: x.score).score
            num_attempts = len(attempts_for_lang)
            language_stats[lang] = {'highest_score': highest_score, 'num_attempts': num_attempts}
        else:
            language_stats[lang] = {'highest_score': 'N/A', 'num_attempts': 0}

    attempted_quiz_languages = {attempt.quiz_language for attempt in user_attempts}
    available_quizzes = {lang for lang in quiz_questions.keys() if lang not in attempted_quiz_languages}

    return render_template('dashboard.html', quiz_questions=quiz_questions, quiz_languages=quiz_questions.keys(), language_stats=language_stats, user_attempts=user_attempts, available_quizzes=available_quizzes)

@app.route('/quiz/<quiz_language>', methods=['GET']) # Changed to GET only
@login_required
def quiz(quiz_language):
    if quiz_language not in quiz_questions:
        flash('Quiz not found!', 'danger')
        return redirect(url_for('dashboard'))

    questions = quiz_questions[quiz_language]

    # FIX: Escape newline characters in explanations for JavaScript
    processed_questions = []
    for q in questions:
        q_copy = q.copy() # Create a copy to avoid modifying the original quiz_questions data
        if 'explanation' in q_copy:
            # Replace single backslash n with double backslash n for JSON compatibility
            q_copy['explanation'] = q_copy['explanation'].replace('\n', '\\n')
        processed_questions.append(q_copy)

    random.shuffle(processed_questions) # Shuffle processed questions for each attempt
    # Store shuffled questions in session to verify answers on submit
    session['current_quiz_questions'] = processed_questions
    session['quiz_start_time'] = datetime.utcnow().timestamp() # Store start time

    return render_template('quiz.html', quiz_language=quiz_language, questions=processed_questions)

@app.route('/submit_quiz/<quiz_language>', methods=['POST'])
@login_required
def submit_quiz(quiz_language):
    if quiz_language not in quiz_questions:
        return jsonify({'error': 'Quiz not found!'}), 404

    user_answers_raw = request.get_json()
    if not user_answers_raw:
        return jsonify({'error': 'No answers submitted.'}), 400

    # Retrieve original questions from session
    stored_questions = session.get('current_quiz_questions')
    if not stored_questions:
        return jsonify({'error': 'Quiz session expired or invalid.'}), 400

    # Calculate time taken
    quiz_start_time = session.pop('quiz_start_time', None)
    time_taken_seconds = 0
    if quiz_start_time:
        time_taken_seconds = int(datetime.utcnow().timestamp() - quiz_start_time)
        # Cap time taken at max quiz duration (300 seconds for 5 minutes)
        if time_taken_seconds > 300:
            time_taken_seconds = 300

    score = 0
    correct_answers_count = 0
    total_questions = len(stored_questions)
    wrong_answers_details = []

    # Create a dictionary for quick lookup of correct answers by question ID
    correct_answers_map = {q['id']: q for q in stored_questions}

    for question_id, user_answer in user_answers_raw.items():
        # The JS now sends actual question IDs, so no need for 'question_' prefix check here
        # Ensure it's a valid question ID from our map
        if question_id in correct_answers_map:
            q_data = correct_answers_map.get(question_id)
            if q_data:
                if user_answer == q_data['correct_answer']:
                    score += 1
                    correct_answers_count += 1
                else:
                    wrong_answers_details.append({
                        'question_id': q_data['id'],
                        'question': q_data['question'],
                        'user_answer': user_answer,
                        'correct_answer': q_data['correct_answer'],
                        'explanation': q_data.get('explanation', 'No explanation provided.')
                    })

    final_score_percentage = (score / total_questions) * 100 if total_questions > 0 else 0

    # Generate AI suggestions (placeholder)
    suggestions = ["Review topics related to your wrong answers.", "Practice more questions.", "Watch relevant video tutorials."]
    if final_score_percentage >= 80:
        suggestions = ["Excellent work! Keep up the great coding.", "Consider trying a more advanced quiz."]
    elif final_score_percentage >= 50:
        suggestions = ["Good effort! Focus on understanding the explanations for incorrect answers.", "Try practicing specific topics."]
    else:
        suggestions = ["Don't worry, every attempt is a learning opportunity. Review the basics and try again!", "Utilize the learning resources available."]

    new_attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_language=quiz_language,
        score=final_score_percentage,
        total_questions=total_questions,
        correct_answers=correct_answers_count,
        time_taken_seconds=time_taken_seconds,
        wrong_answers_details=json.dumps(wrong_answers_details) # Store as JSON string
    )
    db.session.add(new_attempt)
    db.session.commit()

    return jsonify({
        'score': final_score_percentage,
        'correct_answers': correct_answers_count,
        'total_questions': total_questions,
        'wrong_answers_details': wrong_answers_details,
        'suggestions': suggestions,
        'time_taken': time_taken_seconds
    })

@app.route('/result/<int:attempt_id>')
@login_required
def result(attempt_id):
    attempt = db.session.get(QuizAttempt, attempt_id)
    if not attempt or attempt.user_id != current_user.id:
        flash('Attempt not found or you do not have permission to view it.', 'danger')
        return redirect(url_for('dashboard'))

    wrong_answers = json.loads(attempt.wrong_answers_details) if attempt.wrong_answers_details else []

    # Generate AI suggestions for historical results (can be more generic)
    suggestions = ["Review these topics to improve.", "Practice similar questions."]
    if attempt.score >= 80:
        suggestions = ["Great performance!"]
    elif attempt.score >= 50:
        suggestions = ["Good progress!"]
    else:
        suggestions = ["Keep practicing!"]


    return render_template('result.html', attempt=attempt, wrong_answers=wrong_answers, suggestions=suggestions)

@app.route('/videos')
@login_required
def videos():
    return render_template('videos.html')

@app.before_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

