"""Server-like task scheduler and processor."""
import abc
import threading

import six

from jarvis.worker import base

RETRY_INTERVAL = 0.1


@six.add_metaclass(abc.ABCMeta)
class Executor(base.Worker):

    """Contract class for all the executors."""

    def __init__(self, delay, loop):
        super(Executor, self).__init__()
        self._queue = []
        self._delay = delay
        self._loop = loop
        self._stop_event = threading.Event()

    @abc.abstractmethod
    def on_task_done(self, task, result):
        """What to execute after successfully finished processing a task."""
        pass

    @abc.abstractmethod
    def on_task_fail(self, task, exc):
        """What to do when the program fails processing a task."""
        pass

    @abc.abstractmethod
    def on_interrupted(self):
        """What to execute when keyboard interrupts arrive."""
        pass

    def _get_task(self):
        """Retrieves a task from the queue."""
        if self._queue:
            return self._queue.pop()

    def _work(self, task):
        """Run the received task and process the result."""
        # pylint: disable=broad-except
        try:
            return task.run()
        except Exception as exc:
            self.on_task_fail(task, exc)

    def put_task(self, task):
        """Adds a task to the tasks queue."""
        if not isinstance(task, base.Task):
            raise ValueError("Invalid type of task provided.")
        self._queue.append(task)

    def run(self):
        """Processes incoming tasks."""
        self.prologue()
        while not self._stop_event.is_set():
            try:
                task = self._get_task()
                if task:
                    self._work(task)
                if not self._loop:
                    break
            except KeyboardInterrupt:
                self.on_interrupted()
                break
        self.epilogue()


@six.add_metaclass(abc.ABCMeta)
class ConcurrentExecutor(Executor):

    """Abstract base class for concurrent workers."""

    def __init__(self, delay, workers_count, queue_size):
        """Instantiates with custom number thread safe objects."""
        super(ConcurrentExecutor, self).__init__(delay, workers_count)
        self._queue = six.moves.queue.Queue(queue_size)

    def _put_task(self, task):
        """Adds a task to the queue."""
        self._queue.put(task)

    def _get_task(self):
        """Retrieves a task from the queue."""
        return self._queue.get()

    def _start_worker(self):
        """Create a custom worker and return its object."""

        def _worker(self):
            """Worker able to retrieve and process tasks."""
            while not self._stop.is_set():
                task = self._get_task()
                if task:
                    self._work(task)

        worker = threading.Thread(target=_worker)
        worker.setDaemon(True)
        worker.start()
        return worker

    @abc.abstractmethod
    def task_generator(self):
        """Override this with your custom task generator."""
        pass

    def on_task_done(self, task, result):
        """What to execute after successfully finished processing a task."""
        self._queue.task_done()

    def on_task_fail(self, task, exc):
        """What to do when the program fails processing a task."""
        pass

    def on_interrupted(self):
        """Mark the processing as stopped."""
        self._stop_event.set()
        super(ConcurrentExecutor, self).on_interrupted()
