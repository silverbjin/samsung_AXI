from glob import glob
from setuptools import setup

package_name = 'smartdish_ai'
setup(name=package_name, version='0.1.0', packages=[package_name],
      data_files=[('share/ament_index/resource_index/packages', ['resource/' + package_name]),
                  ('share/' + package_name, ['package.xml']),
                  ('share/' + package_name + '/config', glob('config/*.yaml'))],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='SmartDish C', maintainer_email='noreply@example.invalid',
      description='Fail-closed optional SmartDish tray stability inference', license='Apache-2.0',
      entry_points={'console_scripts': ['stability_inference_node = smartdish_ai.stability_inference_node:main']})
