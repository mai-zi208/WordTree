/* 词库数据：2 族 10 词。字段含义见 单词记忆.md 第 2、3 节。
   content = 该词唯一的一条内容（sentence 例句 / story 微故事 / passage 名著片段）
   example + blank = 喂给"例句填空"和"词块成句"的短句
   img = 该词对应的简笔画，同时作为"看图解词"的题干 */

const FAMILIES = [
  {
    family: "spect",
    root: "spect",
    rootMeaning: "看",
    intro: "同一个「看」，看的方向不同，词义就分岔了。",
    words: [
      {
        word: "inspect",
        pos: "v.",
        gloss: "检查；视察",
        part: "in- 往里 + spect 看",
        meme: "往里看：卫生员探头检查厨房",
        content: {
          type: "sentence",
          en: "The health officer inspected the kitchen.",
          zh: "卫生员检查了厨房。"
        },
        example: "The health officer inspected the kitchen.",
        blank: "inspected",
        img: "assets/inspect.png",
        imgZh: "一只手拿放大镜对着厨房角落，照出一只老鼠"
      },
      {
        word: "respect",
        pos: "n./v.",
        gloss: "尊重；敬意",
        part: "re- 回头 + spect 看",
        meme: "回头看第二眼：值得你回头看的分量",
        content: {
          type: "sentence",
          en: "Premier Zhou was a politician worthy of respect.",
          zh: "周总理是一位值得尊重的政治家。"
        },
        example: "I respect people who keep their promises.",
        blank: "respect",
        img: "assets/respect.png",
        imgZh: "一位长者进门，桌边的人都站起来致意"
      },
      {
        word: "prospect",
        pos: "n.",
        gloss: "前景；可能性",
        part: "pro- 向前 + spect 看",
        meme: "向前看：你前方看到的那片东西",
        content: {
          type: "story",
          en: "He stood beside a sheep, imagining the prospect of having a flock of sheep.",
          zh: "他站在一头羊旁，幻想着有一群羊的前景。"
        },
        example: "He imagined the prospect of a big flock.",
        blank: "prospect",
        img: "assets/prospect.png",
        imgZh: "一个人站在吃草的羊旁边，头顶气泡里是一大群羊"
      },
      {
        word: "spectator",
        pos: "n.",
        gloss: "观众；旁观者",
        part: "spect + -ator 做…的人",
        meme: "专门负责看的人：场上跑的是别人，他眼睛比头还大",
        content: {
          type: "sentence",
          en: "A group of spectators watched the game.",
          zh: "一群观众在看比赛。"
        },
        example: "A group of spectators watched the game.",
        blank: "spectators",
        img: "assets/spectator.png",
        imgZh: "看台上一排水火人，中间那个眼睛画得比头大"
      },
      {
        word: "perspective",
        pos: "n.",
        gloss: "视角；观点",
        part: "per- 透过 + spect 看",
        meme: "从你站的位置透过去看：位置一换，世界就换",
        content: {
          type: "story",
          en: "From the bridge the city looked like a circuit board; from the street it looked like home.",
          zh: "从桥上看，这座城市像一块电路板；从街道上看，却像家。"
        },
        example: "Try to see it from my perspective.",
        blank: "perspective",
        img: "assets/perspective.png",
        imgZh: "上格从空中俯瞰城市像电路板，下格街边一栋冒烟的小屋"
      }
    ]
  },
  {
    family: "dict",
    root: "dict",
    rootMeaning: "说",
    intro: "同一个「说」，谁来说、什么时候说、反着说，就是五个不同的词。",
    words: [
      {
        word: "predict",
        pos: "v.",
        gloss: "预言；预测",
        part: "pre- 预先 + dict 说",
        meme: "事情没发生就先说出来：他跑回家时雨还没落下",
        content: {
          type: "sentence",
          en: "Nobody can predict the weather.",
          zh: "没人能预言天气。"
        },
        example: "Nobody can predict the weather.",
        blank: "predict",
        img: "assets/predict.png",
        imgZh: "学生抱着头往家跑，身后乌云和雨点正在聚起来"
      },
      {
        word: "dictionary",
        pos: "n.",
        gloss: "词典；字典",
        part: "dict 说 + -ionary 收集物",
        meme: "把所有人「说过」的都收进一本书里",
        content: {
          type: "story",
          en: "She carried a dictionary not to look words up, but to feel the weight of every word she couldn't say.",
          zh: "她带着一本词典，并非为了查字，而是为了感受每一个无法说出的词的分量。"
        },
        example: "Look it up in a dictionary.",
        blank: "dictionary",
        img: "assets/dictionary.png",
        imgZh: "女孩盘腿坐在靠窗的床上，翻开一本厚词典"
      },
      {
        word: "contradict",
        pos: "v.",
        gloss: "反驳；与…矛盾",
        part: "contra- 反着 + dict 说",
        meme: "反着说：你说鱼不快乐，我说我知道它们快乐",
        content: {
          type: "passage",
          en: "Zhuangzi said the fish were happy. Hui Zi contradicted him: \"You are not a fish — how can you know what pleasure a fish feels?\"",
          zh: "庄子说鱼很快乐。惠子反驳他：你不是鱼，怎么知道鱼的快乐？"
        },
        example: "The evidence contradicts his story.",
        blank: "contradicts",
        img: "assets/contradict.png",
        imgZh: "两个长袍古人站在池边，一个指着水里的鱼，一个抬手回指"
      },
      {
        word: "verdict",
        pos: "n.",
        gloss: "裁决；判决",
        part: "ver- 真实 + dict 说",
        meme: "说出被认定为真的那句：全场只有纸上的几个字在响",
        content: {
          type: "sentence",
          en: "The clerk read the verdict aloud.",
          zh: "书记员大声宣读了判决结果。"
        },
        example: "The clerk read the verdict aloud.",
        blank: "verdict",
        img: "assets/verdict.png",
        imgZh: "一个人站在高台念一张纸，台下几排人坐着听"
      },
      {
        word: "dictate",
        pos: "v.",
        gloss: "口述；支配",
        part: "dict 说 + -ate 使…做",
        meme: "你来说我来写：声波从嘴里飞出去，正好落在别人的笔尖上",
        content: {
          type: "sentence",
          en: "He dictated a letter to his secretary.",
          zh: "他给秘书口述了一封信。"
        },
        example: "He dictated a letter to his secretary.",
        blank: "dictated",
        img: "assets/dictate.png",
        imgZh: "左边一人张口说话，声波飞到右边伏在纸上疾书的人"
      }
    ]
  }
];
