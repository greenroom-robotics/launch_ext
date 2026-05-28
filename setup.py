from setuptools import find_packages
from setuptools import setup
import glob

package_name = "launch_ext"

setup(
    name=package_name,
    version="2.5.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/" + package_name, ["package.xml"]),
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name + "/config", glob.glob("launch_ext/config/*", recursive=True)),
    ],
    install_requires=[
        "setuptools",
        "jinja2",
        # 'launch'
    ],
    zip_safe=True,
    author="Russ Webber",
    author_email="russ.webber@greenroomrobotics.com",
    url="https://github.com/Greenroom-Robotics/launch_ext",
    download_url="https://github.com/Greenroom-Robotics/launch_ext/releases",
    keywords=["ROS"],
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: Software Development",
    ],
    description="Some extras for `launch` tooling.",
    long_description=("Some extras for `launch` tooling."),
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "launch.frontend.launch_extension": [
            "launch_ext = launch_ext",
        ],
    },
)
