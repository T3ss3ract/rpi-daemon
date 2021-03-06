import sys, os, time, psutil, signal
from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
import math

class Daemon(object):
    """
    Usage: - create your own a subclass Daemon class and override the run() method. Run() will be periodically the calling inside the infinite run loop
           - you can receive reload signal from self.isReloadSignal and then you have to set back self.isReloadSignal = False
    """

    def __init__(self, stdin="/dev/null", stdout="/dev/null", stderr="/dev/null"):
        self.ver = 0.1  # version
        self.pauseRunLoop = 0  # 0 means none pause between the calling of run() method.
        self.restartPause = 1  # 0 means without a pause between stop and start during the restart of the daemon
        self.waitToHardKill = 3  # when terminate a process, wait until kill the process with SIGTERM signal
        self.isReloadSignal = False
        self._canDaemonRun = True
        self.processName = os.path.basename(sys.argv[0])
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def _sigterm_handler(self, signum, frame):
        self._canDaemonRun = False

    def _reload_handler(self, signum, frame):
        self.isReloadSignal = True

    def _makeDaemon(self):
        """
        Make a daemon, do double-fork magic.
        """
        try:
            pid = os.fork()
            if pid > 0:
                # Exit first parent.
                sys.exit(0)
        except OSError as e:
            m = f"Fork #1 failed: {e}"
            print(m)
            sys.exit(1)
        # Decouple from the parent environment.
        os.chdir("/")
        os.setsid()
        os.umask(0)
        # Do second fork.
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from second parent.
                sys.exit(0)
        except OSError as e:
            m = f"Fork #2 failed: {e}"
            print(m)
            sys.exit(1)
        m = "The daemon process is going to background."
        print(m)
        # Redirect standard file descriptors.
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self.stdin, "r")
        so = open(self.stdout, "a+")
        se = open(self.stderr, "a+")
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

    def _getProces(self):
        procs = []
        for p in psutil.process_iter():
            if self.processName in [part.split("/")[-1] for part in p.cmdline()]:
                # Skip  the current process
                if p.pid != os.getpid():
                    procs.append(p)
        return procs

    def start(self):
        """
        Start daemon.
        """
        # Handle signals
        signal.signal(signal.SIGINT, self._sigterm_handler)
        signal.signal(signal.SIGTERM, self._sigterm_handler)
        signal.signal(signal.SIGHUP, self._reload_handler)
        # Check if the daemon is already running.
        procs = self._getProces()
        if procs:
            pids = ",".join([str(p.pid) for p in procs])
            m = f"Find a previous daemon processes with PIDs {pids}. Is not already the daemon running?"
            print(m)
            sys.exit(1)
        else:
            m = f"Start the daemon version {self.ver}"
            print(m)
        # Daemonize the main process
        self._makeDaemon()
        # Start a infinitive loop that periodically runs run() method
        self._infiniteLoop()

    def version(self):
        m = f"The daemon version {self.ver}"
        print(m)

    def status(self):
        """
        Get status of the daemon.
        """
        procs = self._getProces()
        if procs:
            pids = ",".join([str(p.pid) for p in procs])
            m = f"The daemon is running with PID {pids}."
            print(m)
        else:
            m = "The daemon is not running!"
            print(m)

    def reload(self):
        """
        Reload the daemon.
        """
        procs = self._getProces()
        if procs:
            for p in procs:
                os.kill(p.pid, signal.SIGHUP)
                m = f"Send SIGHUP signal into the daemon process with PID {p.pid}."
                print(m)
        else:
            m = "The daemon is not running!"
            print(m)

    def stop(self):
        """
        Stop the daemon.
        """
        procs = self._getProces()

        def on_terminate(process):
            m = f"The daemon process with PID {process.pid} has ended correctly."
            print(m)

        if procs:
            for p in procs:
                p.terminate()
            gone, alive = psutil.wait_procs(
                procs, timeout=self.waitToHardKill, callback=on_terminate
            )
            for p in alive:
                m = f"The daemon process with PID {p.pid} was killed with SIGTERM!"
                print(m)
                p.kill()
        else:
            m = "Cannot find some daemon process, I will do nothing."
            print(m)

    def restart(self):
        """
        Restart the daemon.
        """
        self.stop()
        if self.restartPause:
            time.sleep(self.restartPause)
        self.start()

    def _infiniteLoop(self):
        try:
            if self.pauseRunLoop:
                time.sleep(self.pauseRunLoop)
                while self._canDaemonRun:
                    self.run()
                    time.sleep(self.pauseRunLoop)
            else:
                while self._canDaemonRun:
                    self.run()
        except Exception as e:
            m = f"Run method failed: {e}"
            sys.stderr.write(m)
            sys.exit(1)

    # this method you have to override
    def run(self):
        pass

def toRadians(val):
    """

    :param val: value to convert to radians
    :return:    the value to be converted to radians
    """
    one_deg = math.pi / 180
    return one_deg * val


def latlon_distance_calcs(lat1, lng1, lat2, lng2):
    """

    :param lat1: latitude of point 1
    :param lng1: longitude of point 1
    :param lat2: latitude of point 2
    :param lng2: longitude of point 2
    :return: the distance between points 1 and 2
    """
    rlat1 = toRadians(lat1)
    rlng1 = toRadians(lng1)
    rlat2 = toRadians(lat2)
    rlng2 = toRadians(lng2)

    dlong = rlng2 - rlng1
    dlat = rlat2 - rlat1

    ans = math.pow(math.sin(dlat / 2), 2) + math.cos(rlat1) * math.cos(
        rlat2
    ) * math.pow(math.sin(dlong / 2), 2)
    ans = 2 * math.asin(math.sqrt(ans))
    R_miles = 3956
    R_kilometer = 6371
    ans = ans * R_miles
    return ans

def hello_world(request):
    return Response("Hello World!")


def web_system_info(request):
    return Response("webinfo endpoint")


def point_calcs_subdevice(request):
    qs = request.path_qs
    return Response(qs)

def insert_to_pointdb(lat1, lng1):
    return

# ----------------------------------------------------------------------------------------------------
# an example of a custom run method where you can set your useful python code
class MyDaemon(Daemon):
    def run(self):
        config = Configurator()

        config.add_route("hello", "/")
        config.add_route("webinfo", "/webinfo/{item}")
        config.add_route("distance", "/dist/{item}")

        config.add_view(hello_world, route_name="hello")
        config.add_view(web_system_info, route_name="webinfo")
        config.add_view(point_calcs_subdevice, route_name="distance")

        app = config.make_wsgi_app()
        server = make_server("10.0.0.121", 6543, app)
        server.serve_forever()


# ----------------------------------------------------------------------------------------------------
# the main section
if __name__ == "__main__":
    daemon = MyDaemon()
    usageMessage = f"Usage: {sys.argv[0]} (start|stop|restart|status|reload|version)"
    if len(sys.argv) == 2:
        choice = sys.argv[1]
        if choice == "start":
            daemon.start()
        elif choice == "stop":
            daemon.stop()
        elif choice == "restart":
            daemon.restart()
        elif choice == "status":
            daemon.status()
        elif choice == "reload":
            daemon.reload()
        elif choice == "version":
            daemon.version()
        else:
            print("Unknown command.")
            print(usageMessage)
            sys.exit(1)
        sys.exit(0)
    else:
        print(usageMessage)
        sys.exit(1)
