from qwenpaw.extensions import (
    ExtensionRegistry,
    FeaturePolicy,
    ProductSpec,
    qwenpaw_extension,
)


def test_extension_decorator_registers_product_features_and_configure():
    registry = ExtensionRegistry()
    extension = qwenpaw_extension("my_product")

    @extension.product
    def product_spec():
        return ProductSpec(
            product_name="MyProduct",
            cli_name="myproduct",
        )

    @extension.features
    def feature_policy():
        return FeaturePolicy(disabled_features={"builtin_qa_agent"})

    @extension.configure
    def configure(context):
        context.adapters.disable_channel("wechat")

    extension(registry)

    assert registry.product.product_name == "MyProduct"
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False


def test_extension_decorator_can_apply_to_bound_registry():
    registry = ExtensionRegistry()
    extension = qwenpaw_extension("bound_product", registry=registry)

    @extension.product
    def product_spec():
        return ProductSpec(product_name="BoundProduct")

    extension.apply()

    assert registry.product.product_name == "BoundProduct"
