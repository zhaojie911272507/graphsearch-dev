MiroFish 风格语义分块实现完成

  主要改进

  1. 从暴力字符分块改为语义分块

  原来的逻辑 (chunk_text 方法):
  - 使用固定字符窗口滑动（如 500 字符）
  - 忽略段落、句子等语义边界
  - 简单粗暴地按字符数切分

  新的 MiroFish 风格语义分块:
  - 首先识别语义单元：按段落（双换行）分割
  - 智能分组：将段落组合成接近目标大小的块
  - 保持语义完整性：段落、代码块、列表作为整体处理
  - 智能重叠：在句子边界处添加重叠，而非固定字符数

  2. 新增 ChunkNode 元数据字段 (参考 MiroFish 的展示维度)

  class ChunkNode(BaseNode):
      # ... 原有字段

      # MiroFish 风格语义元数据
      section_title: str = ""           # 所属章节标题
      paragraph_type: str = "paragraph" # 内容类型（段落/列表/代码/表格/标题）
      word_count: int = 0               # 字数统计
      sentence_count: int = 0           # 句子数量
      semantic_boundary_start: bool = True  # 是否在语义边界开始
      semantic_boundary_end: bool = True    # 是否在语义边界结束
      previous_chunk_overlap: str = ""  # 与前一块的重叠文本

  3. 智能内容类型检测

  def _detect_paragraph_type(self, text: str) -> str:
      # 识别：code, list, numbered_list, header, table, quote, paragraph

  4. 章节标题自动提取

  def _is_section_header(self, text: str) -> bool:
      # 识别 Markdown 标题（#）、下划线式标题（===）

  def _extract_section_title(self, text: str) -> str:
      # 清理标题格式，提取纯文本

  5. 基于句子边界的重叠

  def _get_overlap_text(self, text: str, max_overlap_chars: int) -> str:
      # 在重叠区域内寻找句子边界，而非简单截断

  测试覆盖

  - 空文本/空白文本处理
  - 短文本单块处理
  - 长文本多块处理
  - 重叠验证
  - 语义元数据完整性
  - 章节标题检测
  - 段落类型识别