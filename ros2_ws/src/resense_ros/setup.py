from glob import glob

from setuptools import setup

package_name = "resense_ros"

setup(
    name=package_name,
    version="0.6.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        ("share/" + package_name + "/rviz", glob("rviz/*.rviz")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ReSense team",
    maintainer_email="team@resense.local",
    description="LiDAR obstacle detection inside the metro train clearance gauge",
    license="MIT",
    entry_points={
        "console_scripts": [
            "detector_node = resense_ros.detector_node:main",
        ],
    },
)
