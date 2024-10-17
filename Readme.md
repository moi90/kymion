# Kymion - A Frontend-Agnostic Progress Reporting Library

**Kymion** is a flexible and extensible Python library designed to provide progress reporting that can be integrated into library code without concern for how progress is visualized.
It provides a simple and intuitive way to track the progress of tasks while allowing the application developer to choose the most appropriate frontend or visualization for their use case.
Similar to Python's [logging](https://docs.python.org/3/library/logging.html) module, different handlers can be used to report progress.

The primary purpose of Kymion is to **decouple progress reporting from its visualization**:
- Libraries can implement progress reporting in a **frontend-agnostic** way.
- Application developers can choose the appropriate frontend or visualization for their context
(like a console progress bar, a REST API endpoint for remote progress tracking, logging progress to a file, a Jupyter notebook widget, a progress bar in a GUI framework).

## Features:

- Frontend-Agnostic: Library developers can use Kymion to report progress without needing to specify how it will be displayed. The application developer can then select a suitable frontend.
- Multiple Frontends: Kymion provides frontends based on popular libraries like tqdm and Rich, with additional flexibility to log progress to files, send updates to REST APIs, or display them in a GUI.
- Multi-Handler Support: Report progress to multiple frontends simultaneously (e.g., console, file logging, and GUI).
- Task Management: Supports tracking multiple tasks, including serial and parallel tasks, making it suitable for complex workflows.

## Basic Usage

Here's how you can integrate Kymion into your code:

### For Library Developers:

```python
from kymion import get_progress_reporter

progress_reporter = get_progress_reporter(__name__)

def my_library_function(data):
    with progress_reporter.task(total=len(data), description="Processing Data") as task:
        for item in data:
            # Process the item...
            task.update()
```

### For Application Developers:
Add the appropriate handler to visualize or log the progress:

```python
from kymion import get_progress_reporter
from kymion.handlers.rich import RichHandler

# Get the root progress reporter
root_progress_reporter = get_progress_reporter()

# Add a RichHandler to display colorful progress bars
root_progress_reporter.add_handler(RichHandler())
```

## Related Work

- [**tqdm**](https://github.com/tqdm/tqdm) provides console-based or notebook-based progress bars. It is known for its simplicity, with very little setup required to add a progress bar to loops or tasks. Still, a rich set of features is available.
- [**Rich**](https://github.com/Textualize/rich) is is a library for text formatting in the terminal and to build console-based UIs. It can be used to display progress bars.
- [**alive-progress**](https://github.com/rsalmei/alive-progress) is another console-based progress bar library with a large number of styles and animations.

All these focus on reporting progress *in the console*. In fact, tqdm-based and Rich-based frontends are available.

### When to Choose Kymion?

- If you're developing a library and want to decouple progress reporting from the presentation layer.
- When you need to support multiple output frontends (e.g., console, GUI, log files) without modifying your core library code.

## **Contributing**

We welcome contributions to Kymion! If you have any suggestions, bug reports, or want to add new features, feel free to open an issue or submit a pull request.

## **License**

Kymion is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
