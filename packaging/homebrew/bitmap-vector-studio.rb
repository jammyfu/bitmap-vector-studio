class BitmapVectorStudio < Formula
  include Language::Python::Virtualenv

  desc "Illustrator-like bitmap/raster to SVG vector conversion studio"
  homepage "https://github.com/jammyfu/bitmap-vector-studio"
  url "https://files.pythonhosted.org/packages/source/b/bitmap-vector-studio/bitmap_vector_studio-0.3.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.11"
  depends_on "cairo"

  resource "bitmap-vector-studio" do
    url "https://files.pythonhosted.org/packages/source/b/bitmap-vector-studio/bitmap_vector_studio-0.3.0.tar.gz"
    sha256 "PLACEHOLDER_SHA256"
  end

  def install
    venv = virtualenv_create(libexec, "python3.11")
    venv.pip_install resources
    venv.pip_install_and_link buildpath
    bin.install_symlink libexec/"bin/vector-studio"
  end

  test do
    system "#{bin}/vector-studio", "--help"
  end
end
