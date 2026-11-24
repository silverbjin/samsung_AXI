from glob import glob
from setuptools import setup

package_name = "smartdish_robot"
setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="SmartDish education",
    maintainer_email="noreply@example.invalid",
    description="SmartDish MVP official Nav2 Navigation Adapter",
    license="Apache-2.0",
    entry_points={"console_scripts": [
        "navigation_adapter = smartdish_robot.navigation_adapter:main",
    ]},
)
