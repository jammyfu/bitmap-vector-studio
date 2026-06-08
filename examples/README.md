# Examples

把测试图片放到本目录后，可以运行：

```bash
vector-studio trace examples/your-image.png --output outputs/your-image.svg --preset poster
```

也可以准备一个 `inputs/` 文件夹进行批量转换：

```bash
vector-studio batch ./inputs ./outputs --preset logo --recursive
```

建议测试素材：

1. 黑白线稿或签名：`--preset bw`
2. Logo / 图标：`--preset logo`
3. 插画或海报：`--preset poster`
4. 照片：`--preset photo`
5. 像素画：`--preset pixel_art`
