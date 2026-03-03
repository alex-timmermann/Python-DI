from python_di.di_container import DependencyInstance
from python_di.example.example_app import ExampleApp
from python_di.example.services.config_b import ConfigB


def main():

    app = ExampleApp.build()

    app.run()
    # or override the dependencies
    app_2 = ExampleApp.build(override_instances=[DependencyInstance(instance_obj=ConfigB(config_b="override"))])

    app_2.run()

if __name__ == "__main__":
    main()